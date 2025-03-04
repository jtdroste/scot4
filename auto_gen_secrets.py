import string
import secrets
import yaml
import sys
import os 
import os.path
import uuid

# Help with YAML formatting comes from here
#https://reorx.com/blog/python-yaml-tips/
class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(IndentDumper, self).increase_indent(flow, False)

def gen_secret(sec_len = 20):
    # Build valid character set 
    valid_chars = string.ascii_letters + string.digits + '!$^&*()'

    # use secrets engine to choose sec_len amount from valid_chars
    # Follows example from here https://docs.python.org/3/library/secrets.html#recipes-and-best-practices
    return ''.join(secrets.choice(valid_chars) for i in range(sec_len))

def gen_apikey():
    # For API Keys, just use uuid
    return str(uuid.uuid4())

def main():
    # See if SQLALCHEMY_DATABASE_URI is on the command line
    sqlalchemy_uri = ''
    if len(sys.argv) > 1:
        sqlalchemy_uri = sys.argv[1]

    # Get path of current file so we can find the secret placeholders
    main_path = os.path.dirname(f"{os.getcwd()}/{sys.argv[0]}")

    # Path of secret files we are modifying
    env_sec_path = f"{main_path}/scot4/secret-skeletons/secrets.yaml"
    flair_sec_path = f"{main_path}/scot4/secret-skeletons/flair-secrets.yaml"

    # Verify placeholder secret files both exist
    if not os.path.isfile(env_sec_path) or not os.path.isfile(flair_sec_path):
        print(f"ERR: Missing one or both of placeholder secret files scot4/secret-skeletons/secrets.yaml, scot4/secret-skeletons/flair-secrets.yaml")

    # Load in env secrets
    with open(env_sec_path, 'r') as file:
        env_sec = yaml.safe_load(file)

    # Load in flair secrets
    with open(flair_sec_path, 'r') as file:
        flair_sec = yaml.safe_load(file)

    # Populate the secrets 
    for item in env_sec["stringData"].keys():
        # Database URI needs values not generated by us, but will initially use API_DB_PASSWORD
        if item == "SQLALCHEMY_DATABASE_URI":
            if sqlalchemy_uri != '':
                env_sec["stringData"][item] = sqlalchemy_uri
        # Enrichment Password needs values not generated by us
        elif item == "ENRICHMENT_PASSWORD":
            env_sec["stringData"][item] = "UPDATE-ME"
        # This needs to be longer to keep meili's engine happy
        elif item == "MEILI_MASTER_KEY":
            env_sec["stringData"][item] = gen_secret(50)
        # Use UUIDs to keep persistent with SCOT's API key gen
        elif item == "FIRST_SUPERUSER_APIKEY" or item == "FLAIR_API_KEY":
            env_sec["stringData"][item] = gen_apikey()
        else:
            env_sec["stringData"][item] = gen_secret()

    # Manually make SEARCH_API_KEY match MEILI_MASTER_KEY
    env_sec["stringData"]["SEARCH_API_KEY"] = env_sec["stringData"]["MEILI_MASTER_KEY"]

    # Insert generated API_DB_PASSWORD into SQLALCHEMY_DATABASE_URI
    DB_PASSWORD = env_sec["stringData"]["API_DB_PASSWORD"]

    if sqlalchemy_uri == "":
        env_sec["stringData"]["SQLALCHEMY_DATABASE_URI"] = env_sec["stringData"]["SQLALCHEMY_DATABASE_URI"].replace("PLACEHOLDER", DB_PASSWORD)

    # Flair Admin pass can be a secret
    flair_sec["stringData"]["S4FLAIR_ADMIN_PASS"] = gen_secret()

    # The following secrets need to match secrets for SCOT API
    flair_sec["stringData"]["S4FLAIR_SCOT_API_KEY"] = env_sec["stringData"]["FIRST_SUPERUSER_APIKEY"]
    flair_sec["stringData"]["S4FLAIR_FLAIR_API_KEY"] = env_sec["stringData"]["FLAIR_API_KEY"]

    # Write the new secrets out to files
    with open(f"{main_path}/scot4/auto_gen_secrets.yaml", 'w+') as file:
        yaml.dump(env_sec, file, Dumper=IndentDumper, sort_keys=False)

    with open(f"{main_path}/scot4/auto_gen_flair_secrets.yaml", 'w+') as file:
        yaml.dump(flair_sec, file, Dumper=IndentDumper, sort_keys=False)

    # Print message to users on what to do next
    help_message = """
    Secrets created for SCOT4 API and Flair. To install the secrets with kubectl:

        FIRST - Populate the secrets for DB credentials and enrichment password
        kubectl -n scot4 apply -f scot4/auto_gen_secrets.yaml
        kubectl -n scot4 apply -f scot4/auto_gen_flair_secrets.yaml
    """
    # print(help_message)  

if __name__ == "__main__":
    main()
