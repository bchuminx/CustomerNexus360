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

