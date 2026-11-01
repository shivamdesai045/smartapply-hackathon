import psycopg2

passwords = ["postgres", "admin", "password", "root", "1234", ""]

success = False
for pwd in passwords:
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password=pwd,
            host="127.0.0.1",
            port="5432"
        )
        print(f"SUCCESS with password: '{pwd}'")
        conn.close()
        success = True
        break
    except Exception as e:
        pass

if not success:
    print("FAILED ALL PASSWORDS")
