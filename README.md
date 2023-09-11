# CustomerNexus360

This project is a graph-based system designed to analyse customer data, purchase history, and account transactions. It leverages the capabilities of Neo4j, a robust graph database, to construct a comprehensive and interconnected representation of your customer interactions.

## Getting Started

To set up and use the project, follow these steps:

1. **Download the Required Plugins**

    To enhance Neo4j's capabilities, you'll need to download two essential plugins: APOC and GDS (Graph Data Science). You can obtain these plugins from the following sources:

    - **APOC**: Download the APOC jar file from [this link](https://github.com/neo4j/apoc/releases/tag/5.11.0) to match your Neo4j version (5.11.0 in this case). Place the downloaded APOC jar file in the `./db/plugins` directory in your project.

    - **GDS (Graph Data Science)**: Download the GDS jar file from [this link](https://github.com/neo4j/graph-data-science/releases) to match your desired version (e.g., version 2.4.5). Place the downloaded GDS jar file in the `./db/plugins` directory in your project.

2. **Additional Configuration**

    2.1 Modify neo4j.conf

    In the `docker/conf` directory, you'll find a `neo4j.conf` file. Copy this file and place it in the appropriate location for your Neo4j installation. Adjust the following settings to enable APOC and GDS and configure memory usage:

    ```conf
    dbms.security.procedures.unrestricted=jwt.security.*,apoc.*,gds.*
    dbms.memory.heap.initial_size=512m
    dbms.memory.heap.max_size=2G
    dbms.memory.pagecache.size=512m
    ```
    In order to enable the APOC and GDS plugins, you'll need to make the following configuration changes in your `neo4j.conf` file. You can find this file in the `docker/conf` directory:

    ```shell
    dbms.security.procedures.unrestricted=jwt.security.*,apoc.*,gds.*
    ```
    This configuration allows full access to these plugins from the Neo4j database.
   
   
    2.2 Enable Arrow for GDS

    For using Arrow with GDS, follow these steps to configure:
    To allow for Arrow configuration, which GDS uses for importing graphs and exporting properties via Apache Arrow Flight, add the following line to the neo4j.conf file:
    ```
    gds.arrow.enabled=true
    ```
    This configuration enables Arrow support in Neo4j when working with GDS.
   
3. **Start Neo4j Container**

    When you bring up the docker for the first time, the `db` is created. 
    Now that you have your Docker Compose file ready and the necessary plugins downloaded, you can start the Neo4j container by running the following command in your project directory:

    ```bash
    docker compose up -d
    ```
4.  **Stop Neo4j Container**
    If you need to stop the container or make changes i.e the neo4j.conf file, you can do so by running:
    ```bash
    docker compose down
    ```
    For example, starting the container the first time will have the db created with the conf folder, after stopping the container, you can place the conf/neo4j.conf file into the db/conf folder and then restart the container.

    You can access the Neo4j Web UI by opening a web browser and navigating to [http://localhost:7474/browser](http://localhost:7474/browser). Log in using the credentials `neo4j` for the username and for the password (as specified in the YAML file). 
Additionally, you have the option to utilize Neo4j Desktop and establish a remote connection. Assign a name to your remote connection and configure the connection URL as follows: ```neo4j://localhost:7687```

## Creating a Conda Environment

To work with this project, it is recommended to create a dedicated Conda environment to manage your dependencies and avoid version conflicts of the existing packages. Follow the steps below to set up the environment and install the required packages.

### 1. Create a New Conda Environment

```bash
conda create --name nexus360 python=3.8.16
```

### 2. Activate the Conda Environment
Activate the newly created environment using the following command:

```bash
conda activate nexus360
```
### 3. Deactivate the Conda Environment
If the Conda environment is no longer in use, you can deactivate it using the following command:

```bash
conda deactivate
```
This command will exit the current Conda environment, returning you to the base environment or the system's default Python environment.

### 3. Install Project Dependencies
Now that you're in the "nexus360" environment, go to the root of the project directory and you can install the project dependencies listed in the requirements.txt file. Run the following command:
```bash
pip install -r requirements.txt
```

This command will install all the necessary Python packages and their specific versions as specified in requirements.txt.
You are now ready to work with the project in the dedicated "nexus360" conda environment. Remember to activate this environment whenever you work on the project to ensure that you are using the correct dependencies.

## Graph Schema

![graph_schema](https://github.com/bchuminx/CustomerNexus360/assets/7111764/0cf2add9-94cd-4b60-8b3f-ad5ce194f6aa)


The graph schema is designed to represent customer data, card information, account transfers, and purchase transactions in a Neo4j graph database. It aims to capture essential information while optimizing data storage and query performance.
### Customer Node
- **Properties**: 
  - CIF (Customer Identification Number)
  - Age
  - Gender (Encoded: 1 for Female, 2 for Male)
  - Latitude
  - Longitude
    Note: The 'Latitude' and 'Longitude' properties are computed using the Geopy library based on the 'Address' and 'Country' information from the 'customers.csv'. The 'Gender' property is encoded using label encoding.
  
### Card Node
- **Properties**:
  - CardNumber (Converted to Integer)
    Note: Initially stored as hyphenated strings in 'customers.csv', later converted to integers.

### Account Node
- **Properties**:
  - AccountNumber (Converted to Integer)
    Note: Initially stored as hyphenated strings in 'customers.csv', later converted to integers.

### Purchase Node (Placeholder)
- **Properties**:
  - Merchant (Mapped to unique IDs using a nodemapper)
  - purchaseAmount
  - purchaseEpoch 
  - purchaseId 
    Note: The 'Purchase' node serves as a placeholder to represent each purchase made by a customer. It is linked to the 'Card' node using the "PURCHASE" relationship.

### Relationships
- **PURCHASE**: Links Customer nodes to Purchase nodes
  - **Properties**: purchaseAmount, purchaseEpoch, purchaseId
  Note: 
    purchaseEpoch: Epoch timestamp calculated from 'PurchaseDatetime' in 'purchases.csv'.
    purchaseId: Taken from 'TransactionID' in 'purchases.csv'.

- **HAS_MERCHANT**: Links Purchase placeholder nodes to Merchant label ('Facebook', etc.)
- **HAS_CARD_ISSUER**: Links Card nodes to CardIssuer label ('Visa', 'MasterCard', 'UnionPay', etc.)

### Account Transfer
Accounts can make transfers between each other
- **TRANSFER**: Represents transfers between Account nodes
  - **Properties**: transactionAmount, transactionId, transferEpoch (Calculated from TransferDatetime as Epoch)

### Additional Information
- The schema focuses on capturing the most essential fields required for Cypher queries.
- Some string values are encoded to optimize storage and queries.
- DateTime values are converted into epoch timestamps.
- Address/country strings are converted into geo-coordinates using Geopy.
- The Graph Data Science library for graph projection supports specific property types but does not support string or datetime types.
- Therefore the data from CSV files is transformed as needed:
  - Strings may be encoded
  - Datetimes converted to epoch values
  - Address/Country strings converted to geo-coordinates

## Running the Application

### neo_arrow_app.py

The neo_arrow_app.py is purpose-built to streamline the ingestion of CSV files into Neo4j, leveraging the Graph Data Science (GDS) client with Arrow Flight streaming enabled. Before running the application, it's essential to ensure that all prerequisites are correctly configured.

#### Prerequisites
Before executing the script, verify that you have met the following prerequisites:

Python: Ensure that you have Python 3.8.16 or a compatible version installed on your system. Refer to the section on "Creating a Conda Environment" for version details.
Dependencies: Install the required Python packages by running the following command with the provided requirements.txt file:

To execute neo_arrow_app.py, follow these steps:
- Open your terminal prompt.
- Navigate to the app directory within the project.
- Run the following command:
```bash
python neo_arrow_app.py
```

## Analysis and Discovery

### Cypher Queries

To run the Cypher queries, use the `cypher_app.py`. You can select a query to run by typing the corresponding number when prompted. 
Please refer to `cypher_app.py` for further description on each of the queries below.
Here are the available queries:

1. **Calculate Total Expenditure of Each Customer:** This query calculates the total expenditure of each customer based on their purchase history.
2. **Calculate Total Expenditure by Merchant for Each Customer:** This query calculates the total expenditure by merchant for each customer.
3. **Filter Purchases by Merchant and Year:** The query filters purchases made at the specified merchant in the year 2021, then groups them by month.
4. **Identify Anomalous Transactions:** This query calculates statistics and assigns anomaly flags for transactions conducted by sender accounts at the first level hop in the network.
5. **Find Cycles Involving Top PageRank Accounts:** The query selects the top 10 accounts based on their PageRank, finds cycles of up to a maximum depth of 10 involving these influential accounts through 'TRANSFER' relationships, and returns those cycles in the graph.
6. **Detect Potential Colluding Accounts:** This query leverages Louvain community detection to uncover potential colluding accounts, surfacing concealed associations within account transfers.
7. **Calculate Average Distance Between Customer Locations:** This query calculates the average distance between pairs of customer locations based on latitude and longitude.
8. **Calculate Pairwise Distances Between Customers:** This query calculates the pairwise distances in kilometers between customers' locations based on their associated accounts, aiming to understand the geographic proximity between customers.
9. **Identify Potential Account Fraud:** This query identifies potential account fraud based on community difference, PageRank, and geographic proximity.

### Running the App

To run the Python scripts (`cypher_app.py`), ensure you have the necessary prerequisites and dependencies installed. You can set up the required environment using the provided `requirements.txt` file. To execute the app, open a terminal, navigate to the project directory, and run:

```bash
python cypher_app.py
```

### NeoDash Dashboard
```neodash.json``` is included in this repository. You can use NeoDash to visualize and explore the Neo4j database.

Launch NeoDash via a web browser at https://neodash.graphapp.io or use NeoDash in the Neo4j Desktop.
Choose "New Dashboard."
Enter your Neo4j database credentials (username and password).
Load the neodash.json file to access the pre-configured dashboard.
The dashboard provides an intuitive interface for exploring your Neo4j database and running queries interactively.

### Neo4j Bloom
![bloom_customernexus360](https://github.com/bchuminx/CustomerNexus360/assets/7111764/8f98857c-d438-458f-b5c1-be53dfc49d17)

Neo4j Bloom is a powerful tool for visualizing and exploring graph data stored in Neo4j databases. It provides an intuitive interface for creating and running graph queries while also enabling interactive exploration of graph structures. In this project, Neo4j Bloom is used to complement the analysis capabilities provided by Cypher queries.

### Launching Neo4j Bloom

You can access Neo4j Bloom directly from the Neo4j Desktop, similar to launching NeoDash. Follow these steps:

1. Open Neo4j Desktop and select your current active database.
2. In the top-right corner of the Neo4j Desktop interface, click the dropdown box.
3. Find and select "Neo4j Bloom" from the available options.

### Using Neo4j Bloom

Once Neo4j Bloom is launched, you can use it to visualize and explore your graph data. One of the powerful features of Neo4j Bloom is the ability to create custom queries and visualize their results.

#### Custom Queries in Neo4j Bloom

In this project, I've added a custom query to Neo4j Bloom that was defined in the `cypher_app.py` for the cyclic detection of account transfers. This query helps you identify patterns in account transfers within your customer graph.

#### Adding a Search Phrase
When defining a custom query in Neo4j Bloom, you will need to add a meaningful search phrase. A search phrase allows you to quickly access and run the query when working with your graph data.

#### Leveraging Graph Data Science
Neo4j Bloom supports the use of Graph Data Science algorithms, which can be layered onto your visualizations to enhance the interpretability of the results. For example, in this project, I've used both PageRank and Louvain community detection algorithms to enrich the results visualisation.
- **PageRank:** This algorithm assigns importance scores to nodes, making larger nodes more prominent. It helps to identify key entities in the graph.
- **Louvain Community Detection:** This algorithm identifies communities or clusters of nodes that share similar characteristics, and from the communityId, Bloom assigns the same color to nodes within the same community.

