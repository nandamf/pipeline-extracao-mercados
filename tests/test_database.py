import sqlite3
import pandas as pd

conn = sqlite3.connect(
    "database/produtos.db"
)

df = pd.read_sql(
    """
    SELECT
        rede,
        COUNT(*) quantidade
    FROM produtos
    GROUP BY rede
    """,
    conn
)

conn.close()

print(df)