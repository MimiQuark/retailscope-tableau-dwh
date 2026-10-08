from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
TABLEAU_DIR = BASE_DIR / "output" / "tableau"
TWB = TABLEAU_DIR / "RetailSalesDashboard-Professional.twb"
TWBX = TABLEAU_DIR / "RetailSalesDashboard-Professional.twbx"
SOURCE_DATA = Path(r"C:\Users\27800\Desktop\RetailSalesDashboard_Data")
PACKAGE_DIR = "Data/RetailSalesDashboard_Data"


def finalize():
    tree = ET.parse(TWB)
    root = tree.getroot()
    for ds in root.findall("./datasources/datasource"):
        old = ds.find("connection")
        if old is None or old.get("class") != "textscan":
            continue
        filename = old.get("filename")
        old_columns = list(ds.findall("column"))
        position = list(ds).index(old)
        ds.remove(old)
        connection_name = f"textscan.{ds.get('name').split('.')[-1]}"
        connection = ET.Element("connection", {"class": "federated"})
        named_connections = ET.SubElement(connection, "named-connections")
        named_connection = ET.SubElement(named_connections, "named-connection", {"caption": ds.get("caption", ""), "name": connection_name})
        ET.SubElement(named_connection, "connection", {"class": "textscan", "directory": PACKAGE_DIR, "filename": filename, "password": "", "server": ""})
        table_name = f"[{Path(filename).stem}#csv]"
        relation = ET.SubElement(connection, "relation", {"connection": connection_name, "name": filename, "table": table_name, "type": "table"})
        columns = ET.SubElement(relation, "columns", {"character-set": "UTF-8", "header": "yes", "locale": "zh_CN", "separator": ","})
        for ordinal, column in enumerate(old_columns):
            ET.SubElement(columns, "column", {"datatype": column.get("datatype", "string"), "name": column.get("caption", column.get("name", "").strip("[]")), "ordinal": str(ordinal)})
        ds.insert(position, connection)
    ET.indent(tree, space="  ")
    tree.write(TWB, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(TWBX, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(TWB, TWB.name)
        for csv_file in SOURCE_DATA.glob("*.csv"):
            archive.write(csv_file, f"{PACKAGE_DIR}/{csv_file.name}")
    print(TWB)
    print(TWBX)


if __name__ == "__main__":
    finalize()