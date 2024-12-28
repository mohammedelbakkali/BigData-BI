import logging
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.providers.postgres.hooks.postgres import PostgresHook

import json
import csv
from airflow.providers.mysql.hooks.mysql import MySqlHook
import re
from pyspark.sql import  Row
from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook

from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.utils.dates import days_ago
from airflow.decorators import task
from pyspark.sql import SparkSession
from airflow.providers.microsoft.mssql.operators.mssql import MsSqlOperator
import pyodbc

def verify_and_convert_structure(t):
    result = []

    for idx, item in enumerate(t):
        print(f"Processing item {idx}: Type: {type(item)}, Content: {item}")

        if isinstance(item, dict) and all(key in item for key in ["Title", "DOI", "Authors"]):
            article = {
                "Title": item.get("Title"),
                "DOI": item.get("DOI"),
                "Authors": item.get("Authors"),
                "Publication Date": item.get("Publication Date", None),  # Ajout d'une valeur par défaut si absent
                "ISSN": item.get("ISSN", None),  # Idem pour ISSN
                "Link": item.get("Link", None),
                "Quartils": item.get("Quartils", "Journal pas indexé Scopus"),  # Valeur par défaut pour Quartils
                "journal_main": f"Published in: {item.get('Title', 'Unknown')}",  # Utilisation du titre ou d'une valeur par défaut
                "abstract": item.get("abstract", None)  # Si l'abstract est présent
            }
            result.append(article)
        else:
            print(f"Skipping invalid item {idx}: {item}")

    return result

       


#JZvTaDMmQwpr9V8
default_args = {
    'owner': 'admin',
    'start_date': datetime(2023, 12, 28),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


@dag(
    dag_id='pipeline',
    schedule_interval='@daily',
    start_date=datetime(2023, 12, 28),
    catchup=False
)
def pipeline():
    @task()
    def fetch_data_from_mongo():
        try:
            # Initialize the Mongo hook and get the MongoDB connection
            hook = MongoHook(mongo_conn_id='mongo_default')
            client = hook.get_conn()

            # Access your MongoDB database and collection
            collection = client['bigdata']['journals']

            # Fetch data from the collection
            cursor = collection.find()  # This returns a cursor to iterate over the documents

            # Convert the documents to a list of dictionaries and serialize ObjectId
            data_list = []
            for document in cursor:
                document['_id'] = str(document['_id'])  # Convert ObjectId to string
                data_list.append(document)

            # Print the data in JSON format
            print(json.dumps(data_list, indent=4))  # Pretty print the JSON
             
            return data_list  # This can be returned if needed for further tasks

        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            return None

    # @task()
    # def fetch_data_from_postgres():
    #     try:
    #         # Initialize the Postgres hook
    #         postgres_hook = PostgresHook(postgres_conn_id='postgres_default')

    #         # SQL query to fetch data from users table
    #         sql_query = "SELECT * FROM journals;"

    #         # Execute the query
    #         connection = postgres_hook.get_conn()
    #         cursor = connection.cursor()
    #         cursor.execute(sql_query)

    #         # Fetch and print the data
    #         data = cursor.fetchall()
    #         for row in data:
    #             print(row)

    #         return data  # Return data for potential further processing

    #     except Exception as e:
    #         print(f"Error connecting to PostgreSQL: {e}")
    #         return None

    # @task()
    # def fetch_data_from_json():
    #     try:
    #         json_file_path = 'C:/Users/mohammed/Desktop/Airflow/Data-Engineering-Pipeline/airflow/data_set/journals.json'

    #         # Open and load JSON data
    #         with open(json_file_path, 'r') as file:
    #             data = json.load(file)

    #         # Print or process the JSON data
    #         print(json.dumps(data, indent=4))
    #         return data  # Return data if needed for further tasks

    #     except Exception as e:
    #         print(f"Error reading JSON file: {e}")
    #         return None

    @task()
    def push_data_in_postgres(data):
        postgres_hook = PostgresHook(postgres_conn_id='postgres_default_2')
    
        try:
        # Vérifier la connexion à la base de données PostgreSQL
            connection = postgres_hook.get_conn()
            print("Connexion réussie à PostgreSQL")
        
        # Créer un curseur pour exécuter des requêtes
            cursor = connection.cursor()

        # Vérifier si la base de données 'journal' existe déjà
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'journal';")
            exists = cursor.fetchone()

            if not exists:
            # Créer la base de données 'journal' si elle n'existe pas
                cursor.execute("CREATE DATABASE journal;")
                print("Base de données 'journal' créée avec succès.")
            else:
                print("La base de données 'journal' existe déjà.")

        except Exception as e:
            print(f"Erreur lors de la connexion à PostgreSQL : {e}")
        finally:
        # Fermer le curseur et la connexion
            if connection:
                connection.close()
    @task()
    def test_sql():
        mssql_hook = MsSqlHook(mssql_conn_id='mssql_default')
        with mssql_hook.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO journal (JournalMain, ISSN, Quartils)
                    OUTPUT inserted.JournalID
                    VALUES ('Static Test Journal', '5678-1234', 'test');
                    """
                )
                journal_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"Static journal inserted successfully with ID {journal_id}.")



    @task()
    def setup_database():
    # Connexion à la base de données PostgreSQL
        postgres_hook = PostgresHook(postgres_conn_id='postgres_default_2')
    
        try:
        # Vérifier la connexion à la base de données
            connection = postgres_hook.get_conn()
            print("Connexion réussie à PostgreSQL")

            cursor = connection.cursor()

        # Créer la base de données si elle n'existe pas
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'journal';")
            exists = cursor.fetchone()
            if not exists:
                cursor.execute("CREATE DATABASE journal;")
                print("Base de données 'journal' créée avec succès.")
            else:
                print("La base de données 'journal' existe déjà.")

        # Requêtes SQL à exécuter (création de tables)
            queries = [
            """DROP TABLE IF EXISTS "authors"; 
            CREATE TABLE "authors" (
                "AuthorID" serial PRIMARY KEY, 
                "AuthorName" varchar(100) NOT NULL, 
                "Affiliation" varchar(255), 
                "Country" varchar(100)
            );""",
            
            """DROP TABLE IF EXISTS "Date"; 
            CREATE TABLE "Date" (
                "DateID" serial PRIMARY KEY, 
                "FullDate" date NOT NULL, 
                "Year" int, 
                "Month" int, 
                "Day" int
            );""",
            
            """DROP TABLE IF EXISTS "Journal"; 
            CREATE TABLE "Journal" (
                "JournalID" serial PRIMARY KEY, 
                "JournalMain" varchar(255) NOT NULL, 
                "ISSN" varchar(50), 
                "Quartils" varchar(50)
            );""",
            
            """DROP TABLE IF EXISTS "Publicationauthors"; 
            CREATE TABLE "Publicationauthors" (
                "PublicationID" int NOT NULL, 
                "AuthorID" int NOT NULL, 
                PRIMARY KEY ("PublicationID", "AuthorID"),
                FOREIGN KEY ("AuthorID") REFERENCES "authors" ("AuthorID")
            );""",
            
            """DROP TABLE IF EXISTS "Publications"; 
            CREATE TABLE "Publications" (
                "PublicationID" serial PRIMARY KEY, 
                "Title" varchar(255) NOT NULL, 
                "DOI" varchar(100), 
                "PublicationDate" date, 
                "Link" varchar(255), 
                "Abstract" text, 
                "JournalID" int, 
                FOREIGN KEY ("JournalID") REFERENCES "Journal" ("JournalID")
            );""",
            
            """DROP TABLE IF EXISTS "Quartils"; 
            CREATE TABLE "Quartils" (
                "QuartilID" serial PRIMARY KEY, 
                "annee" varchar(4) NOT NULL, 
                "quartil" varchar(255), 
                "id_journal" int, 
                FOREIGN KEY ("id_journal") REFERENCES "Journal" ("JournalID")
            );"""
        ]

        # Exécution des requêtes pour créer les tables
            for query in queries:
                cursor.execute(query)
                print(f"Exécution de la requête : {query[:50]}...")  # Affichage du début de la requête pour suivi

        # Commit des changements
            connection.commit()

            print("Tables créées avec succès.")

        except Exception as e:
            print(f"Erreur lors de la connexion ou de l'exécution des requêtes : {e}")
        finally:
            if connection:
                connection.close()
                print("Connexion fermée.")

    @task()
    def preTraitement(data_from_mongo):
        try:
            # Initialiser la session Spark
            spark = SparkSession.builder.appName("PySpark Example").getOrCreate()

            # Les données MongoDB sont déjà passées en paramètre (data_from_mongo)
            data_list = data_from_mongo

            # Convertir la liste de documents MongoDB en DataFrame PySpark
            df = spark.read.json(spark.sparkContext.parallelize([json.dumps(item) for item in data_list]))

            # Afficher le DataFrame original
            df.show(truncate=False)

            # 1. Supprimer les objets avec des titres répétés (éliminer la redondance)
            df_no_duplicates = df.dropDuplicates(["Title"])

            # 2. Supprimer les valeurs nulles dans les colonnes essentielles
            # Supprimer les lignes contenant des valeurs nulles dans les colonnes Title, DOI, et Publication Date
            df_cleaned = df_no_duplicates.dropna(subset=["Title", "DOI", "Publication Date"])

            # Afficher le DataFrame nettoyé
            df_cleaned.show(truncate=False)

            # Définir le chemin où enregistrer le fichier Parquet
            output_path = "/opt/airflow/tmp/filtered_data.parquet"

            # Sauvegarder le DataFrame nettoyé en tant que fichier Parquet
            df_cleaned.write.parquet(output_path)

            # Arrêter la session Spark après le travail
            spark.stop()

            # Retourner le chemin du fichier Parquet via XCom
            return output_path

        except Exception as e:
            print(f"Error: {e}")
            return None

    @task()
    def read_parquet_and_convert_to_mongo(parquet_path):
        try:
        # Initialiser SparkSession
            spark = SparkSession.builder.appName("Parquet to MongoDB").getOrCreate()

        # Lire le fichier Parquet
            print(f"Lecture du fichier Parquet depuis : {parquet_path}")
            df = spark.read.parquet(parquet_path)

        # Afficher un aperçu des données
            print("DataFrame chargé depuis le Parquet :")
            df.show(truncate=False)

        # Fonction pour nettoyer les lignes du DataFrame
            def clean_row(row):
            # Convertir un objet Row en dictionnaire
                row_dict = row.asDict()

            # Nettoyer chaque valeur
                for key, value in row_dict.items():
                    if isinstance(value, list):
                    # Traiter les listes
                        row_dict[key] = [
                        v.asDict() if isinstance(v, Row) else v for v in value
                    ]
                    elif isinstance(value, Row):
                    # Traiter les objets Row imbriqués
                        row_dict[key] = value.asDict()
                    elif isinstance(value, str) and value.startswith("[") and value.endswith("]"):
                    # Décoder les chaînes JSON en listes ou dictionnaires
                        try:
                            row_dict[key] = json.loads(value)
                        except json.JSONDecodeError:
                            pass  # Si ce n'est pas un JSON valide, laisser tel quel
                return row_dict

        # Appliquer le nettoyage à chaque ligne
            cleaned_data = [clean_row(row) for row in df.collect()]

        # Arrêter la SparkSession
            spark.stop()

        # Afficher un exemple de données nettoyées
            print("Documents MongoDB nettoyés :")
            print(json.dumps(cleaned_data[:2], indent=2, ensure_ascii=False))

            return cleaned_data

        except Exception as e:
            print(f"Erreur lors de la conversion du fichier Parquet : {e}")
            return None


    


    @task()
    def insert_data_into_data_warehouse(input):

        print(input)

        #mysql_hook = MySqlHook(mysql_conn_id="mysql_default")
        #postgres_hook = PostgresHook(postgres_conn_id='postgres_default_2')
        mssql_hook = MsSqlHook(mssql_conn_id='mssql_default')
        data = verify_and_convert_structure(input)
        print(data)

        def add_authors(authors):
            try:
                mssql_hook = MsSqlHook(mssql_conn_id='mssql_default')
                with mssql_hook.get_conn() as conn:
                    with conn.cursor() as cursor:
                        author_ids = []

                        # Loop through authors list
                        for author_name in authors:
                            # Check if the author already exists
                            cursor.execute(
                                "SELECT AuthorID FROM authors WHERE AuthorName = %s",
                                (author_name,)
                            )
                            result = cursor.fetchone()

                            if result:
                                # Author exists, use the existing AuthorID
                                author_id = result[0]
                                logging.info(f"Author '{author_name}' already exists with ID {author_id}.")
                            else:
                                # Author does not exist, insert a new record with None for Affiliation and Country
                                cursor.execute(
                                    """
                                    INSERT INTO authors (AuthorName, Affiliation, Country)
                                    OUTPUT inserted.AuthorID
                                    VALUES (%s, NULL, NULL)
                                    """,
                                    (author_name,)
                                )
                                author_id = cursor.fetchone()[0]
                                logging.info(f"Author '{author_name}' added with ID {author_id}.")

                            author_ids.append(author_id)

                        return author_ids  # Return list of author IDs

            except Exception as e:
                logging.error(f"Error adding authors: {e}")
                return None




        # Function to get or create a journal entry
        def determine_quartile_from_citescore(citescore):
            """Déterminer le quartil basé sur le CiteScore."""
            if citescore >= 4.0:
                return "Q1"
            elif citescore >= 2.0:
                return "Q2"
            elif citescore >= 1.0:
                return "Q3"
            else:
                return "Q4"

        def process_quartil(quartil_value):
            """Vérifier si le quartil est un nombre et le transformer en quartil valide."""
            try:
                # Si le quartil est un nombre, déterminer le quartil approprié
                quartil_float = float(quartil_value)

                # Retourner le quartil basé sur la valeur numérique
                return determine_quartile_from_citescore(quartil_float)
            except ValueError:
                # Si ce n'est pas un nombre, il doit être déjà sous forme de quartil (par exemple "Q1", "Q2", ...)
                return quartil_value  # Retourner le quartil tel quel s'il est valide (Q1, Q2, etc.)

        def get_or_create_journal(journal_main, issn, quartils):
            try:
                mssql_hook = MsSqlHook(mssql_conn_id='mssql_default')
                with mssql_hook.get_conn() as conn:
                    with conn.cursor() as cursor:
                        logging.info(f"Inspecting quartils for journal '{journal_main}': {quartils} - Type: {type(quartils)}")

                        # Validation et normalisation des quartils
                        if isinstance(quartils, str):
                            if "pas indexé" in quartils.lower():
                                logging.info(f"Detected non-indexed journal: '{quartils}'.")
                                quartils = []
                            else:
                                logging.warning(f"Unexpected Quartils string for journal '{journal_main}': {quartils}. Setting to empty list.")
                                quartils = []
                        elif isinstance(quartils, list):
                            quartils = [
                                q for q in quartils if isinstance(q, dict) and 'année' in q and 'quartil' in q
                            ]
                        else:
                            logging.warning(f"Unexpected Quartils type for journal '{journal_main}': {type(quartils)}. Setting to empty list.")
                            quartils = []

                        # Extraction de l'ISSN
                        electronic_issn = 'Non disponible'
                        if isinstance(issn, dict):
                            electronic_issn = issn.get('Electronic ISSN', 'Non disponible')
                        elif isinstance(issn, str):
                            electronic_issn = issn

                        # Vérification ou insertion du journal
                        cursor.execute("SELECT JournalID FROM Journal WHERE JournalMain = %s", (journal_main,))
                        result = cursor.fetchone()
                        if result:
                            journal_id = result[0]
                            logging.info(f"Journal '{journal_main}' already exists with ID {journal_id}.")
                        else:
                            quartil_value = 'indexe' if quartils else 'pas indexe'
                            logging.info(f"Inserting journal with parameters: {journal_main}, {electronic_issn}, {quartil_value}")
                            cursor.execute(
                                """
                                INSERT INTO Journal (JournalMain, ISSN, Quartils)
                                OUTPUT inserted.JournalID
                                VALUES (%s, %s, %s);
                                """,
                                (journal_main, electronic_issn, quartil_value)
                            )
                            journal_id = cursor.fetchone()[0]
                            logging.info(f"Journal '{journal_main}' inserted successfully with ID {journal_id}.")

                        # Insérer les quartils (uniquement si non vide)
                        for quartil in quartils:
                            try:
                                annee = quartil.get('année')
                                quartil_value = quartil.get('quartil')
                                if not annee or not quartil_value:
                                    logging.warning(f"Invalid quartil entry: {quartil}. Skipping.")
                                    continue
                                cursor.execute(
                                    """
                                    MERGE INTO Quartils AS target
                                    USING (SELECT %s AS annee, %s AS quartil, %s AS id_journal) AS source
                                    ON target.annee = source.annee AND target.id_journal = source.id_journal
                                    WHEN MATCHED THEN
                                        UPDATE SET quartil = source.quartil
                                    WHEN NOT MATCHED THEN
                                        INSERT (annee, quartil, id_journal)
                                        VALUES (source.annee, source.quartil, source.id_journal);
                                    """,
                                    (annee, quartil_value, journal_id)
                                )
                                logging.info(f"Quartil successfully inserted/updated for Annee: {annee}, JournalID: {journal_id}")
                            except Exception as e:
                                logging.error(f"Error inserting/updating quartil: {quartil} - Error: {e}")

                        conn.commit()
                        return journal_id

            except Exception as e:
                logging.error(f"Error creating or retrieving journal '{journal_main}': {e}")
                return None


        



        def extract_journal_name(journal_main):
            # Regular expression to capture the journal name
            match = re.search(r"Published in:\s*([^(\n]+)", journal_main)
            if match:
                journal_name = match.group(1).strip()  # Capture the matched group and strip any surrounding whitespace
                return journal_name
            return None  # Return None if no match is found

        # Function to insert a publication entry
        def insert_publication(title, doi, publication_date, link, abstract, journal_id, last_quartil):
            try:
                mssql_hook = MsSqlHook(mssql_conn_id='mssql_default')
                with mssql_hook.get_conn() as conn:
                    with conn.cursor() as cursor:
                        # Log des paramètres
                        logging.info(f"Inserting publication with parameters: Title={title}, DOI={doi}, "
                                     f"PublicationDate={publication_date}, Link={link}, Abstract={abstract}, "
                                     f"JournalID={journal_id}, Quartils={last_quartil}")

                        # Insérer la publication et récupérer l'ID inséré
                        cursor.execute(
                            """
                            INSERT INTO publications (Title, DOI, PublicationDate, Link, Abstract, JournalID, Quartils)
                            OUTPUT inserted.PublicationID
                            VALUES (%s, %s, %s, %s, %s, %s, %s);
                            """,
                            (title, doi, publication_date, link, abstract, journal_id, last_quartil)
                        )
                        publication_id = cursor.fetchone()[0]  # Récupérer l'ID de la publication
                        conn.commit()  # Valider la transaction
                        logging.info(f"Publication '{title}' inserted successfully with ID {publication_id}.")
                        return publication_id

            except Exception as e:
                logging.error(f"Error inserting publication '{title}': {e}")
                return None




        # Iterate over each publication in the data
        for entry in data:
            try:
                journal_main = extract_journal_name(entry.get('journal_main', '')) 
                issn = entry.get('ISSN', {})
                quartils = entry.get('Quartils', [])
                authors = entry.get('authors', [])
                add_authors(authors)
                publication_date_str = entry.get('Publication Date', '').replace("Date of Publication: ", "")
                publication_date = datetime.strptime(publication_date_str, "%d %B %Y").date() if publication_date_str else None
                doi = entry.get('DOI', '')
                title = entry.get('Title', '')
                link = entry.get('Link', '')
                abstract = entry.get('abstract', '')

                # Vérification des types de données
                if not isinstance(quartils, (str, list)):
                    logging.warning(f"Unexpected type for quartils: {type(quartils)}. Setting to empty list.")
                    quartils = []

                # Création ou récupération du journal
                journal_id = get_or_create_journal(journal_main, issn, quartils)
                if not journal_id:
                    logging.warning(f"Journal '{journal_main}' was not inserted.")
                    continue
                
                # Insertion de la publication
                last_quartil = quartils[-1].get('quartil', 'Non disponible') if quartils else 'Non disponible'
                insert_publication(title, doi, publication_date, link, abstract, journal_id, last_quartil)

            except Exception as e:
                logging.error(f"Error processing publication '{entry.get('Title', '')}': {e}")


    @task()
    def add_author():
        postgres_hook = PostgresHook(postgres_conn_id='postgres_default_2')
        author_name="simooo"
        try:
            with postgres_hook.get_conn() as conn:
                with conn.cursor() as cursor:
                    # Vérifier si l'auteur existe déjà
                    cursor.execute(
                        "SELECT authorid FROM authors WHERE authorname = %s",
                        (author_name,)
                    )
                    result = cursor.fetchone()

                    if result:
                        # L'auteur existe déjà, retourner son ID
                        author_id = result[0]
                        logging.info(f"L'auteur '{author_name}' existe déjà avec l'ID {author_id}.")
                    else:
                        # Ajouter un nouvel auteur
                        cursor.execute(
                            """
                         INSERT INTO authors (AuthorName, Affiliation, Country)
                         OUTPUT inserted.AuthorID
                         VALUES (?, NULL, NULL)

                            """,
                            (author_name,)
                        )
                        # Récupérer l'ID de l'auteur nouvellement inséré
                        author_id = cursor.fetchone()[0]
                        conn.commit()
                        logging.info(f"Auteur '{author_name}' ajouté avec succès avec l'ID {author_id}.")

                    return author_id
        except Exception as e:
            logging.error(f"Erreur lors de l'ajout de l'auteur '{author_name}': {e}")
            return None
    @task()
    def test_insert_static_with_params():
        try:
            # Stockez les paramètres dans des variables
            journal_main = "Test Journal Static with Params"
            issn = "5678-1234"
            quartils = "indexe"

            # Créez une connexion avec MsSqlHook
            mssql_hook = MsSqlHook(mssql_conn_id='mssql_default')
            with mssql_hook.get_conn() as conn:
                with conn.cursor() as cursor:
                    # Ajoutez un log pour afficher les paramètres
                    logging.info(f"Parameters to insert: JournalMain={journal_main}, ISSN={issn}, Quartils={quartils}")

                    # Exécutez la requête SQL en utilisant %s pour les placeholders
                    cursor.execute(
                        """
                        INSERT INTO journal (JournalMain, ISSN, Quartils)
                        OUTPUT inserted.JournalID
                        VALUES (%s, %s, %s);
                        """,
                        (journal_main, issn, quartils)
                    )

                    # Récupérez l'ID inséré
                    journal_id = cursor.fetchone()[0]
                    conn.commit()
                    logging.info(f"Static journal inserted successfully with ID {journal_id}.")

        except Exception as e:
            logging.error(f"Error during static insert with parameters: {e}")


    # Define task dependencies
    mongo_data = fetch_data_from_mongo()
    #postgres_data = fetch_data_from_postgres()
    #json_data = fetch_data_from_json()

    data = preTraitement(mongo_data)
    dataframetomongo = read_parquet_and_convert_to_mongo(data)
    insert_data_into_data_warehouse  = insert_data_into_data_warehouse(dataframetomongo)
    #insert_data_into_data_warehouse  = insert_data_into_data_warehouse(mongo_data)
    #add_author = add_author()
    #insert_data_task_from_postgres  = insert_data_into_data_warehouse(postgres_data)
    # Set the order of execution

    #setup = setup_database()
    #mongo_data  >> data >> insert_data_task_from_mongo
     
    #mongo_data >> data >> dataframetomongo >> add_author
    #test_insert_static_with_params = test_insert_static_with_params()
    mongo_data >> data >> dataframetomongo  >> insert_data_into_data_warehouse
    
# Set the DAG to run
pipeline()