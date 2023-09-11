"""
cypher_app.py

Description:
The app.py include Cypher queries enabled by both GDS and APOC, to discover insights related to customer accounts, purchases and merchants from the CustomerGraph.

Author: Benjamin Chu
Date: 11-09-2023
"""

import logging
import os
import pandas as pd

from dotenv import load_dotenv
from graphdatascience import GraphDataScience

load_dotenv()

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
CATALOG = "AccountGraph"

gds = GraphDataScience("bolt://"+NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD), database="customernexus360")

log = logging.getLogger('cypher')
logging.basicConfig(level=logging.INFO)

def init_graph():
    g1_node_projection = ['Account']
    g1_relationship_projection = {"TRANSFER": {"orientation": "NATURAL"}}

    # Before actually going through with the projection, check how much memory is required
    results = gds.graph.project.estimate(g1_node_projection, g1_relationship_projection)

    log.info(" Required memory for native loading >> " + str(results['requiredMemory']))

    if gds.graph.exists(CATALOG)['exists']:
        gds.graph.get(CATALOG).drop()
    else:
        G1, _ = gds.graph.project(CATALOG, g1_node_projection, g1_relationship_projection)

        pagerank_metadata = gds.pageRank.write(G1, writeProperty='pagerank')
        log.info(pagerank_metadata)

        louvain_metadata = gds.louvain.write(G1, writeProperty='communityId')
        log.info(louvain_metadata)

# Run and log the Cypher query with description and results
def run_query(cypher_query, query_name, query_description):
    # Run the Cypher query and get the results as a DataFrame
    results_df = gds.run_cypher(cypher_query)

    # Log the query name
    log.info(f"[{query_name}]")
    # Log the query description
    log.info("\nDescription -> " + query_description)
    
    # Convert the DataFrame to a JSON format
    json_result = results_df.to_json(orient='records')

    # Log the formatted JSON query results
    log.info("\nResults -> \n" + json_result)
    log.info("\n\n")

if __name__ == "__main__":
    init_graph()

    while True:
        log.info("  Select a query to run from 1-6 or type 'Q' to exit:")
        log.info("  [Q1] Calculate total expenditure of each customer based on purchase history.")
        log.info("  [Q2] Calculate total expenditure by merchant for each customer.")
        log.info("  [Q3] The query filters purchases made at the specified merchant in the year 2021, then groups them by month.")
        log.info("  [Q4] The query calculates the stats and assign anomaly flags for transactions conducted by sender accounts at the first level hop in the network.")
        log.info("  [Q5] The query selects the top 10 accounts based on their PageRank, finds cycles of up to maximum depth of 10 involving these `influential` accounts through 'TRANSFER' relationships, and returns those cycles in the graph.")
        log.info("  [Q6] The query leverages Louvain community detection to uncover potential colluding accounts, surfacing concealed associations within account transfers.")

        user_input = input("\nEnter the query number or 'Q' to exit: ")

        if user_input == 'Q':
            log.info("  Exit")
            break  # Exit when the user types 'exit'

        try:
            selected_query = int(user_input)

            if selected_query == 1:
                '''
                    QUERY-1: 
                '''
                q1_description = (
                "The query calculates the total expenditure of each customer, based on their purchase history."
                "It offers a quick overview of customer spending patterns."
                )
                q1_cypher = """
                    MATCH (c:Customer)-[:HAS_CARD]->(:Card)-[p:PURCHASE]->(:Purchase)
                    RETURN c.CIF AS CIF, ROUND(SUM(p.purchaseAmount), 2) AS TotalExpenditure
                """
                run_query(q1_cypher, "QUERY-1", q1_description)

            elif selected_query == 2:
                '''
                    QUERY-2: 
                '''
                q2_description = (
                "The query calculates the total expenditure of each customer, based on their purchase history."
                "It offers a quick overview of customer spending patterns."
                )
                q2_cypher = """
                    MATCH (c:Customer)-[:HAS_CARD]->(card)-[r:PURCHASE]->(purchase)-[:HAS_MERCHANT]->(merchant)
                    WITH c.CIF AS CustomerID, COLLECT(labels(merchant)) AS MerchantNames, ROUND(SUM(r.purchaseAmount), 2) AS Total_Expenditure
                    WITH CustomerID, apoc.coll.flatten(MerchantNames) AS MerchantNames, Total_Expenditure
                    WITH CustomerID, apoc.coll.frequencies(MerchantNames) AS MerchantFrequencies, Total_Expenditure
                    UNWIND MerchantFrequencies AS output 
                    WITH CustomerID, output.item + ':' + output.count AS MerchantCountConcatenated, Total_Expenditure
                    RETURN CustomerID, COLLECT(MerchantCountConcatenated) AS Merchant_Counts, Total_Expenditure
                    ORDER BY Total_Expenditure DESC
                """
                run_query(q2_cypher, "QUERY-2", q2_description)
            
            elif selected_query == 3:
                '''
                    QUERY-3: 
                '''
                q3_description = (
                "The query filters purchases made at the specified merchant in the year 2021, then groups them by month."
                "It provides a monthly count of unique customers who made purchases at this specified merchant providing quick insights into customer engagement over time."
                )
                q3_cypher = """
                    MATCH (n)<-[:HAS_MERCHANT]-(p:Purchase)-[r:PURCHASE]-(x)
                    WHERE 'Facebook' IN labels(n)
                    WITH p, r, datetime({ epochMillis: toInteger(r.purchaseEpoch) * 1000 }) AS purchaseDateTime
                    WHERE purchaseDateTime.year = 2021
                    WITH p, purchaseDateTime.month AS purchaseMonth
                    MATCH (p)-[:PURCHASE]-(:Card)-[:HAS_CARD]-(c:Customer)
                    RETURN purchaseMonth AS Month, COUNT(DISTINCT c) AS TotalCount
                    ORDER BY purchaseMonth
                """
                run_query(q3_cypher, "QUERY-3", q3_description)

            elif selected_query == 4:
                '''
                    QUERY-4: 
                '''
                q4_description = (
                "The query calculates the stats and assign anomaly flags for transactions conducted by sender accounts at the first level hop in the network."
                "It provides the view on transaction patterns and identifies sender accounts with potentially unusual transaction behaviour based on mean, median, and standard deviation metrics."
                "Based on all the flagged anomalies based on mean, median, and standard deviation, it will finally assign the final anomaly flag based on the union of all these values."
                )
                q4_cypher = """
                    //Calculate overall stats for all transactions
                    MATCH ()-[r:TRANSFER]->()
                    WITH r.transactionAmount AS allAmounts

                    WITH AVG(allAmounts) AS OverallMeanTransactionAmount,
                    percentileCont(allAmounts, 0.5) AS OverallMedianTransactionAmount,
                    STDEV(allAmounts) AS OverallStandardDeviationTransactionAmount

                    // Calculate the stats for transaction amounts for each sender account
                    MATCH (sender:Account)-[r:TRANSFER]->(receiver:Account)
                    WITH sender, r.transactionAmount AS amounts, OverallMeanTransactionAmount, OverallMedianTransactionAmount, OverallStandardDeviationTransactionAmount

                    WITH sender,
                    amounts,
                    OverallMeanTransactionAmount,
                    OverallMedianTransactionAmount,
                    OverallStandardDeviationTransactionAmount,
                    // Calculate anomaly scores
                    CASE
                    WHEN ABS(AVG(amounts) - OverallMeanTransactionAmount) > 1000 THEN 1
                    ELSE 0
                    END AS MeanAnomalyScore,
                    CASE
                    WHEN ABS(percentileCont(amounts, 0.5) - OverallMedianTransactionAmount) > 1000 THEN 1
                    ELSE 0
                    END AS MedianAnomalyScore,
                    CASE
                    WHEN ABS(STDEV(amounts) - OverallMeanTransactionAmount) > 1000 THEN 1
                    ELSE 0
                    END AS StdDevAnomalyScore

                    RETURN sender.AccountNumber AS SenderAccountNumber,
                    COUNT(amounts) AS TransactionCount,
                    AVG(amounts) AS MeanTransactionAmount,
                    percentileCont(amounts, 0.5) AS MedianTransactionAmount,
                    STDEV(amounts) AS StandardDeviationTransactionAmount,
                    OverallMeanTransactionAmount, // Include overall statistics in the result
                    OverallMedianTransactionAmount,
                    OverallStandardDeviationTransactionAmount,
                    MeanAnomalyScore,
                    MedianAnomalyScore,
                    StdDevAnomalyScore,
                    // Calculate the combined Anomaly field
                    CASE
                    WHEN MeanAnomalyScore = 1 AND MedianAnomalyScore = 1 AND StdDevAnomalyScore = 1 THEN 1
                    ELSE 0
                    END AS Anomaly
                    ORDER BY Anomaly DESC;
                """
                run_query(q4_cypher, "QUERY-4", q4_description)

            elif selected_query == 5:
                '''
                    QUERY-5: 
                '''
                #note: the results produced is better suited for visualization or viewing in NeoDash
                q5_description = (
                "The query selects the top 10 accounts based on their PageRank, finds cycles of up to maximum depth of 10 involving these `influential` accounts through 'TRANSFER' relationships, and returns those cycles in the graph."
                "It specifically aims to identify closed-loop transaction patterns, where the start and end accounts are the same."
                "This is crucial in detecting potential money laundering or fraud activities, as closed-loop transactions may indicate attempts to obscure the flow of funds within a network."
                )
                q5_cypher = """
                    MATCH (a:Account)
                    WITH a
                    ORDER BY a.PageRank DESC
                    LIMIT 10
                    WITH collect(a) AS topAccounts
                    CALL apoc.nodes.cycles(topAccounts, {relTypes: ["TRANSFER"], maxDepth: 10}) 
                    YIELD path 
                    WITH path, length(path) AS pathLength
                    ORDER BY pathLength DESC
                    RETURN path
                """
                run_query(q5_cypher, "QUERY-5", q5_description)

            elif selected_query == 6:
                '''
                    QUERY-6: 
                '''
                #note: the results produced is better suited for visualization or viewing in NeoDash
                q6_description = (
                "The query leverages Louvain community detection to uncover potential colluding accounts, surfacing concealed associations within account transfers."
                "This will e useful in identifying abnormal cluster sizes, flagging potentially fraudulent activities involving numerous accounts for further investigation."
                )
                q6_cypher = """
                    MATCH (a1:Account)-[r:TRANSFER]->(a2:Account)
                    WHERE r.transactionAmount >= 5000

                    WITH COLLECT(DISTINCT a1) + COLLECT(DISTINCT a2) AS nodes

                    UNWIND nodes AS node
                    WITH DISTINCT node.communityId AS communityId, COLLECT(DISTINCT node.AccountNumber) AS accountsInCommunity
                    WITH communityId, accountsInCommunity, size(accountsInCommunity) AS communitySize
                    WHERE communitySize > 1
                    RETURN communityId, accountsInCommunity
                    ORDER BY communitySize DESC
                """
                run_query(q6_cypher, "QUERY-6", q6_description)
            else:
                log.info("Invalid query number. Please select a number from 1 to 6.")
        except ValueError:
            log.error("Invalid input. Please enter a valid number.")