# -*- coding: utf-8 -*-
"""
Created on Sun Mar 29 21:49:32 2026

@author: EMMANUEL KLESSON
"""

import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# 👑 admin
cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', '1234', 'admin')")

# 👤 utilisateur
cursor.execute("INSERT INTO users (username, password, role) VALUES ('emmanuel', '1234', 'user')")

# 👤 membre
cursor.execute("INSERT INTO members (name, phone) VALUES ('emmanuel', '0700000000')")

# 🔗 liaison
cursor.execute("UPDATE users SET member_id = 1 WHERE username = 'emmanuel'")

conn.commit()
conn.close()

print("✅ Setup terminé")