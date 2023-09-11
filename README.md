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
