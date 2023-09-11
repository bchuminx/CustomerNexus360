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
    
    gds.run_cypher("""
        MATCH (c:Customer)
        SET c.Coordinate = point({latitude: toFloat(c.Latitude), longitude: toFloat(c.Longitude)})
        RETURN DISTINCT COUNT(c)
    """)

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
        log.info("  [Q7] This query calculates the average distance between pairs of customer locations based on latitude and longitude.")
        log.info("  [Q8] This query calculates the pairwise distances in kilometers between customers' locations based on their associated accounts, aiming to understand the geographic proximity between customers.")
        log.info("  [Q9] This query identifies potential account fraud based on community difference, PageRank, and geographic proximity.")

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
                "This will be useful in identifying abnormal cluster sizes, flagging potentially fraudulent activities involving numerous accounts for further investigation."
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

            elif selected_query == 7:
                '''
                    QUERY-7: 
                '''
                q7_description = (
                "This query calculates the average distance between pairs of customer locations based on latitude and longitude."
                "This is essential for understanding the spatial distribution of customers and can help in identifying clustering patterns based on proximity."
                )
                q7_cypher = """
                MATCH (c1:Customer), (c2:Customer)
                WHERE id(c1) < id(c2)  // To avoid duplicate pairs
                WITH ROUND(toFloat(point.distance(point({latitude: c1.Latitude, longitude: c1.Longitude}), point({latitude: c2.Latitude, longitude: c2.Longitude}))/1000), 2) AS dist
                RETURN AVG(dist) AS AverageDistanceInKM
                """
                run_query(q7_cypher, "QUERY-7", q7_description)
                
            elif selected_query == 8:
                '''
                    QUERY-8: 
                '''
                q8_description = (
                "This query calculates the pairwise distances in kilometers between customers' locations based on their associated accounts, aiming to understand the geographic proximity between customers."
                "This is useful to establish expected patterns of behavior on customers; when customers typically conduct account transfers within a certain geographic region, sudden transfers from distant locations may raise suspicion and signal potential fraudulent activities."
                )
                q8_cypher = """
                MATCH (c1:Customer)-[:HAS_ACCOUNT]->(a:Account)
                WITH c1, a, point({latitude: c1.Latitude, longitude: c1.Longitude}) AS customerLocationA
                MATCH (c2:Customer)-[:HAS_ACCOUNT]->(b:Account)
                WHERE id(c1) < id(c2) // To avoid duplicate pairs
                WITH c1, a, b, customerLocationA, c2, point({latitude: c2.Latitude, longitude: c2.Longitude}) AS customerLocationB
                WITH c1, a, b, customerLocationA, c2, customerLocationB, ROUND(toFloat(point.distance(customerLocationA, customerLocationB)/1000), 2) AS DistanceInKM
                RETURN c1.CIF AS C1, a.AccountNumber AS C1_AccountNumber, c2.CIF AS C2, b.AccountNumber AS C2_AccountNumber, DistanceInKM
                ORDER BY DistanceInKM
                LIMIT 100
                """
                run_query(q8_cypher, "QUERY-8", q8_description)

            elif selected_query == 9:
                '''
                    QUERY-9: 
                '''
                q9_description = (
                "This query identifies pairs of accounts involved in transfers that exhibit suspicious behavior based on community differences, PageRank, and geographic distance."
                "Calculate the difference in community IDs, compare PageRank values, and measure the distances between customers and accounts."
                "Thresholds can be set for community difference, PageRank, and geographic distance to define suspicious account transfers."
                "Suspicious account transfers can include transfers to accounts with higher PageRank, significant community ID differences, and geographic distances exceeding the specified thresholds."
                )
                q9_cypher = """
                MATCH (c1:Customer)-[:HAS_ACCOUNT]->(a:Account)-[:TRANSFER]->(b:Account)<-[:HAS_ACCOUNT]-(c2:Customer)
                WHERE id(c1) < id(c2)  // To avoid duplicate pairs
                WITH a, b, c1, c2,
                    abs(a.communityId - b.communityId) AS communityDifference, // Calculate community ID difference
                    a.pagerank AS sourcePageRank, b.pagerank AS targetPageRank // Get PageRank for source and target accounts
                WITH a, b, c1, c2, communityDifference, sourcePageRank, targetPageRank,
                    point({latitude: c1.Latitude, longitude: c1.Longitude}) AS customerLocationC1,
                    point({latitude: c2.Latitude, longitude: c2.Longitude}) AS customerLocationC2
                WITH a, b, c1, c2, communityDifference, sourcePageRank, targetPageRank, customerLocationC1, customerLocationC2,
                    point.distance(customerLocationC1, customerLocationC2)/1000 AS distanceBetweenCustomersInKM
                WHERE communityDifference > 1 // Define a threshold for community ID difference
                AND sourcePageRank < targetPageRank // Consider only transfers to higher PageRank accounts
                AND distanceBetweenCustomersInKM > 5000
                RETURN a.AccountNumber AS C1_AccountNumber, b.AccountNumber AS C2_AccountNumber, c1.CIF AS C1_CIF, c2.CIF AS C2_CIF, communityDifference, sourcePageRank, targetPageRank, distanceBetweenCustomersInKM
                """
                run_query(q9_cypher, "QUERY-9", q9_description)

            else:
                log.info("Invalid query number. Please select a number from 1 to 9.")
        except ValueError:
            log.error("Invalid input. Please enter a valid number.")