from typing import Annotated
from fastmcp import FastMCP
from pydantic import Field
import requests

mcp = FastMCP("GeoconnexMCP")

def query_geoconnex(query_text: str):
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/sparql-query",
    }
    GEOCONNEX_GRAPH = "https://graph.geoconnex.us/"
    response = requests.post(
        GEOCONNEX_GRAPH, data=query_text.encode("utf-8"), headers=headers
    )
    response.raise_for_status()  # Raises an error if the request failed
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from Geoconnex: {response.text}") from e

@mcp.tool
def geoconnex_shacl_shape() -> str:
    """A SHACL shape that describes the structure of RDF data in the Geoconnex graph database. Not all data will conform to this shape, but it is a good general guideline of what data is available."""
    url = "https://raw.githubusercontent.com/internetofwater/nabu/refs/heads/main/shacl_validator/shapes/geoconnex.ttl"
    response = requests.get(url)
    response.raise_for_status()
    return response.text    

@mcp.tool
def explore_geoconnex_db(sparql_query: Annotated[str, Field(description="A SPARQL query to run against the Geoconnex database that can be used to explore the database and discover what data is available")]) -> str:
    """Search through the Geoconnex graph database and discover info about what data is available. The Geoconnex graph database is a RDF database of hydrological features in the United States."""
    return query_geoconnex(sparql_query)

@mcp.tool
def get_geoconnex_pid_from_river_name(river_name: Annotated[str, Field(description="The name of the river")]) -> str:
    """Given a river name, search the Geoconnex graph database for the associated persistent identifier (PID) and return it."""
    result = query_geoconnex(f"""
    PREFIX hyf: <https://www.opengis.net/def/schema/hy_features/hyf/>
    PREFIX gsp: <http://www.opengis.net/ont/geosparql#>
    PREFIX schema: <https://schema.org/>

    SELECT DISTINCT ?mainstem ?name ?wkt
    WHERE {{
    BIND("{river_name}" AS ?searchString)
    
    # flowpath allows us to filter by mainstems
    ?mainstem a hyf:HY_FlowPath ;
                schema:name ?name ;
                gsp:hasGeometry/gsp:asWKT ?wkt .

    # Case-insensitive substring match
    FILTER(CONTAINS(LCASE(STR(?name)), LCASE(STR(?searchString))))
    }}
    ORDER BY ?name
    """)
    assert result
    assert "results" in result
    for res in result["results"]["bindings"]:
        return res["mainstem"]["value"]
    return "No PID found"

@mcp.tool
def get_datasets_for_geoconnex_pid(pid: Annotated[str, Field(description="The Geoconnex persistent identifier (PID) of the river")]) -> list:
    """Given a PID, return a list of datasets associated with the river."""
    query = f"""
    PREFIX schema: <https://schema.org/>
    PREFIX gsp: <http://www.opengis.net/ont/geosparql#>
    PREFIX hyf: <https://www.opengis.net/def/schema/hy_features/hyf/>
    
    SELECT DISTINCT ?monitoringLocation ?siteName ?datasetDescription ?type ?url
                    ?variableMeasured ?variableUnit ?measurementTechnique ?temporalCoverage
                    ?distributionName ?distributionURL ?distributionFormat ?wkt
    WHERE {{
        VALUES ?mainstem {{ <{pid}> }}
        
        ?monitoringLocation hyf:referencedPosition/hyf:HY_IndirectPosition/hyf:linearElement ?mainstem ;
                            schema:subjectOf ?item ;
                            hyf:HydroLocationType ?type ;
                            gsp:hasGeometry/gsp:asWKT ?wkt .

        ?item schema:name ?siteName ;
              schema:temporalCoverage ?temporalCoverage ;
              schema:url ?url ;
              schema:variableMeasured ?variableMeasured .

        ?variableMeasured schema:description ?datasetDescription ;
                          schema:name ?variableMeasuredName ;
                          schema:unitText ?variableUnit ;
                          schema:measurementTechnique ?measurementTechnique .

        OPTIONAL {{
            ?item schema:distribution ?distribution .
            ?distribution schema:name ?distributionName ;
                          schema:contentUrl ?distributionURL ;
                          schema:encodingFormat ?distributionFormat .
        }}

        # Filter datasets by the desired variable description
        FILTER(REGEX(?datasetDescription, "temperature", "i"))
    }}
    ORDER BY ?siteName
    LIMIT 5
    """
    result = query_geoconnex(query)
    assert result
    assert "results" in result
    return result["results"]["bindings"]

if __name__ == "__main__":
    mcp.run()