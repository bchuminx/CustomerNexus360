"""
neo_arrow_app.py

Description:
The app.py processes CSV files and using Graph Data Science (GDS) client with Arrow Flight streaming enabled for ingestion into Neo4j. It manages data preparation and loading, ensuring CSV data is transformed and structured appropriately.

Author: Benjamin Chu
Date: 11-09-2023
"""

import logging
import os
import pandas as pd

from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from graphdatascience import GraphDataScience
from pydantic import BaseModel
from sklearn.preprocessing import LabelEncoder
from typing import Union

load_dotenv()

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]

gds = GraphDataScience("bolt://"+NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD), arrow=True)
# Necessary if Arrow is enabled
gds.set_database("neo4j")

log = logging.getLogger('csv_to_graph')
logging.basicConfig(level=logging.INFO)

# Create a LabelEncoder instance
gender_encoder = LabelEncoder()

class NodeItem(BaseModel):
    node_index: int
    value: Union[int, str]
    label: str

def read_csv(file_path):
    return pd.read_csv(file_path)

def convert_to_int(value):
    value = str(value)
    return int(value.replace('-', ''))

def get_lat_long(row):
    address = row['Address']
    country = row['Country']
    
    geolocator = Nominatim(timeout=10, user_agent="geolocator")
    location = geolocator.geocode(address)
    
    if location is not None:
        return pd.Series({'Latitude': location.latitude, 'Longitude': location.longitude})
    else:
        location = geolocator.geocode(country)
        return pd.Series({'Latitude': location.latitude, 'Longitude': location.longitude})

def create_nodes_from_dataframe(df, label_value_pairs, starting_index):
    nodes = []
    index = starting_index

    for _, row in df.iterrows():
        for label, column_name in label_value_pairs.items():
            if column_name in df.columns:
                value = row[column_name]
                node = NodeItem(
                    node_index=index,
                    value=value,
                    label=label
                )
                nodes.append(node)
                index += 1
    return nodes

def map_values_to_node_ids(nodes, label_filter=None):
    value_to_node_id = {}

    for node in nodes:
        if label_filter is None or node.label == label_filter:
            value_to_node_id[node.value] = node.node_index
    return value_to_node_id


# main execution of the app.py
if __name__ == "__main__":
    customer_df = read_csv('../data/customers.csv')

    # Check if 'Latitude' and 'Longitude' columns do not exist
    if 'Latitude' not in customer_df.columns or 'Longitude' not in customer_df.columns:
        log.info("Converting addresses to geo-coordinates")
        # Apply the get_lat_long function to the "Address", "Country" columns and create new columns "Latitude" and "Longitude"
        customer_df[['Latitude', 'Longitude']] = customer_df.apply(get_lat_long, axis=1)
        log.info("Coordinates conversion is completed")
    
    # Apply the convert_to_int function to 'AccountNumber' and 'CardNumber'
    customer_df['AccountNumber'] = customer_df['AccountNumber'].apply(convert_to_int)
    customer_df['CardNumber'] = customer_df['CardNumber'].apply(convert_to_int)

    # Fit and transform the 'Gender' column
    customer_df['Gender_Encoded'] = gender_encoder.fit_transform(customer_df['Gender']) + 1 

    transaction_df = read_csv('../data/transfers.csv')
    transaction_df['TransactionID'] = transaction_df['TransactionID'].astype(int)
    transaction_df['SenderAccountNumber'] = transaction_df['SenderAccountNumber'].str.replace('-', '').astype(int)
    transaction_df['ReceiverAccountNumber'] = transaction_df['ReceiverAccountNumber'].str.replace('-', '').astype(int)
    transaction_df['Amount'] = transaction_df['Amount'].astype(float)
    transaction_df['TransferDatetime'] = pd.to_datetime(transaction_df['TransferDatetime']).dt.tz_convert('UTC')
    transaction_df['TransferEpoch'] = (transaction_df['TransferDatetime'] - pd.Timestamp('1970-01-01 00:00:00+00:00', tz='UTC')).dt.total_seconds().astype(int)

    purchase_df = read_csv('../data/purchases.csv')
    purchase_df['CardNumber'] = purchase_df['CardNumber'].str.replace('-', '').astype(int)
    purchase_df['Merchant'] = purchase_df['Merchant'].str.replace(' ', '_')
    purchase_df['PurchaseDatetime'] = pd.to_datetime(purchase_df['PurchaseDatetime']).dt.tz_convert('UTC')
    purchase_df['PurchaseEpoch'] = (purchase_df['PurchaseDatetime'] - pd.Timestamp('1970-01-01 00:00:00+00:00', tz='UTC')).dt.total_seconds().astype(int)

    # Filter out duplicate merchant values in the purchase_df dataFrame
    distinct_merchant_df = purchase_df.drop_duplicates(subset='Merchant') 

    # Filter out duplicate card issuer values in the purchase_df DataFrame
    distinct_card_issuer_df = purchase_df.drop_duplicates(subset='CardIssuer')

    # Remove duplicates based on pairs of 'CardNumber' and 'CardIssuer'
    distinct_card_issuer_to_card = purchase_df.drop_duplicates(subset=['CardNumber', 'CardIssuer'])

    label_value_pairs_customer = {'Customer': 'CIF', 'Account': 'AccountNumber', 'Card': 'CardNumber'}
    label_value_pairs_purchase= {'Purchase': 'TransactionID'}
    label_value_pairs_merchant = {'Merchant': 'Merchant'}
    label_value_pairs_card_issuers = {'CardIssuer': 'CardIssuer'}

    customer_nodes = create_nodes_from_dataframe(customer_df, label_value_pairs_customer, starting_index=1)
    purchase_nodes = create_nodes_from_dataframe(purchase_df, label_value_pairs_purchase, starting_index=max(node.node_index for node in customer_nodes)+1)
    merchant_nodes = create_nodes_from_dataframe(distinct_merchant_df, label_value_pairs_merchant, starting_index=max(node.node_index for node in purchase_nodes)+1)
    card_issuer_nodes = create_nodes_from_dataframe(distinct_card_issuer_df, label_value_pairs_card_issuers, starting_index=max(node.node_index for node in merchant_nodes)+1)

    nodes = customer_nodes + purchase_nodes + merchant_nodes + card_issuer_nodes

    placeholder_merchant_node = NodeItem(
        node_index=len(nodes) + 1,
        value='Merchant',
        label='Merchant'
    )  

    nodes.append(placeholder_merchant_node)
    
    # Create a dictionary to map node_index to value
    node_index_to_value = {node.node_index: node.value for node in nodes}

    cif_to_node_id = map_values_to_node_ids(nodes, 'Customer')
    account_number_to_node_id = map_values_to_node_ids(nodes, 'Account')
    card_number_to_node_id = map_values_to_node_ids(nodes, 'Card')
    merchant_to_node_id = map_values_to_node_ids(nodes, 'Merchant')
    purchase_to_node_id = {node.value: node.node_index for node in nodes if node.label == 'Purchase'}


    # Create customer_properties dataframe
    customer_properties = pd.DataFrame().assign(
        nodeId=customer_df['CIF'].map(cif_to_node_id),
        CIF=customer_df['CIF'].tolist(),
        labels="Customer",
        Age=customer_df['Age'].tolist(),
        Gender=customer_df['Gender_Encoded'].tolist(),
        Latitude=customer_df['Latitude'].tolist(),
        Longitude=customer_df['Longitude'].tolist()
    )

    # Create transaction_properties dataframe
    transaction_properties = pd.DataFrame().assign(
        transactionId=transaction_df['TransactionID'],
        senderId=transaction_df['SenderAccountNumber'].map(account_number_to_node_id),
        receiverId=transaction_df['ReceiverAccountNumber'].map(account_number_to_node_id),
        SenderAccountNumber=transaction_df['SenderAccountNumber'].tolist(),
        ReceiverAccountNumber=transaction_df['ReceiverAccountNumber'].tolist(),
        Amount=transaction_df['Amount'],
        TransferEpoch=transaction_df['TransferEpoch']
    )

    # Create account_properties dataframe
    account_properties = pd.DataFrame().assign(
        nodeId=customer_df['AccountNumber'].map(account_number_to_node_id),
        labels="Account",
        AccountNumber=customer_df['AccountNumber'].tolist()
    )

    # Create card_properties dataframe
    card_properties = pd.DataFrame().assign(
        nodeId=customer_df['CardNumber'].map(card_number_to_node_id),
        labels="Card",
        CardNumber=customer_df['CardNumber'].tolist()
    )

    # Create purchase_properties dataframe
    purchase_properties = pd.DataFrame().assign(
        nodeId=purchase_df['TransactionID'].map(purchase_to_node_id),
        labels="Purchase",
        Merchant=purchase_df['Merchant'].map(merchant_to_node_id)
    )

    # Create merchant_properties dataframe
    merchant_properties = pd.DataFrame().assign(
        nodeId=distinct_merchant_df['Merchant'].map(merchant_to_node_id),
        labels=distinct_merchant_df['Merchant'].tolist()
    )
    data_to_append = pd.DataFrame({'nodeId': [placeholder_merchant_node.node_index], 'labels': ['Merchant']})
    merchant_properties = pd.concat([merchant_properties, data_to_append], ignore_index=True)

    # Create a dictionary to map card_issuer to nodeId
    card_issuer_to_node_id = {node.value: node.node_index for node in nodes if node.label == 'CardIssuer'}

    # Create card_issuer_properties dataframe
    card_issuer_properties = pd.DataFrame().assign(
        nodeId=distinct_card_issuer_df['CardIssuer'].map(card_issuer_to_node_id),
        labels=distinct_card_issuer_df['CardIssuer'].tolist()
    )

    all_properties = pd.concat([customer_properties[["nodeId", "labels"]], account_properties[["nodeId", "labels"]], card_properties[["nodeId", "labels"]], purchase_properties[["nodeId", "labels"]], merchant_properties[["nodeId", "labels"]], card_issuer_properties[["nodeId", "labels"]]])
    
    customer_ids = all_properties[all_properties['labels'] == 'Customer']['nodeId'].tolist()
    account_ids = all_properties[all_properties['labels'] == 'Account']['nodeId'].tolist()
    card_ids = all_properties[all_properties['labels'] == 'Card']['nodeId'].tolist()
    purchase_ids = all_properties[all_properties['labels'] == 'Purchase']['nodeId'].tolist()
    merchant_ids = [node_id for node_id in merchant_properties['nodeId'].tolist() if node_id != placeholder_merchant_node.node_index]

    account_transaction_ids = transaction_properties['transactionId'].tolist()
    sender_ids = transaction_properties['senderId'].tolist()
    receiver_ids = transaction_properties['receiverId'].tolist()
    account_amount_list = transaction_properties['Amount'].tolist()

    purchase_merchant_ids = purchase_properties['Merchant'].tolist()
    purchase_transaction_ids = purchase_df['TransactionID'].tolist()
    purchase_amount_list = purchase_df['Amount'].tolist()

    R1 = pd.DataFrame().assign(sourceNodeId=customer_ids, targetNodeId=account_ids, relationshipType="HAS_ACCOUNT")
    R2 = pd.DataFrame().assign(sourceNodeId=sender_ids, targetNodeId=receiver_ids, relationshipType="TRANSFER", transactionId=account_transaction_ids, transactionAmount=account_amount_list, transferEpoch=transaction_properties['TransferEpoch'].tolist())
    R3 = pd.DataFrame().assign(sourceNodeId=customer_ids, targetNodeId=card_ids, relationshipType="HAS_CARD")
    R4 = pd.DataFrame().assign(sourceNodeId=merchant_ids, targetNodeId=placeholder_merchant_node.node_index, relationshipType="HAS_TYPE")
    R5 = pd.DataFrame().assign(sourceNodeId=purchase_df['CardNumber'].map(card_number_to_node_id).tolist(), targetNodeId=purchase_ids, relationshipType="PURCHASE", purchaseId=purchase_transaction_ids, purchaseAmount=purchase_amount_list, purchaseEpoch=purchase_df['PurchaseEpoch'].tolist())
    R6 = pd.DataFrame().assign(sourceNodeId=purchase_ids, targetNodeId=purchase_merchant_ids, relationshipType="HAS_MERCHANT")
    R7 = pd.DataFrame().assign(sourceNodeId=distinct_card_issuer_to_card['CardNumber'].map(card_number_to_node_id).tolist(), targetNodeId=distinct_card_issuer_to_card['CardIssuer'].map(card_issuer_to_node_id).tolist(), relationshipType="HAS_CARD_ISSUER")

    # Construct the graph
    customer_graph = gds.graph.construct(
        "customer-load-graph",
        [customer_properties, account_properties, card_properties, purchase_properties, merchant_properties, card_issuer_properties],
        [R1, R2, R3, R4, R5, R6, R7]
    )

    gds.run_cypher("""CALL gds.graph.export('customer-load-graph', { dbName: 'customernexus360' })""")
    customer_graph.drop()