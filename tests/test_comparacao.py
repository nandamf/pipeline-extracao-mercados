import sqlite3
import pandas as pd

conn = sqlite3.connect(
    "database/produtos.db"
)

df = pd.read_sql(
    """
    SELECT
        descricao,
        rede,
        preco_unitario
    FROM produtos
    WHERE descricao LIKE '%Ninho%'
    ORDER BY preco_unitario
    """,
    conn
)

conn.close()

print(df)