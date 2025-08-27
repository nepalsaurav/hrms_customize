import json
import requests
from bs4 import BeautifulSoup


def get_employee_attendance(year: str, month: str) -> dict:
    """
     Example:
        attendance_dict = {
            "emp001": [
                {"employee_name": "Alice", "date": "01-08-2026", "status": "Present"},
                {"employee_name": "Alice", "date": "02-08-2026", "status": "Absent"}
            ],
            "emp002": [
                {"employee_name": "Bob", "date": "01-08-2026", "status": "Present"}
            ]
        }
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    })

    r = session.get("http://192.168.200.26/digilog/MonthlyReport.aspx")
    soup = BeautifulSoup(r.content, "html.parser")

    hidden_inputs = soup.find_all("input", type="hidden")
    payload = {hidden.get("name"): hidden.get("value") for hidden in hidden_inputs}

    payload.update({
        "ctl00$main$ddlCompany": "1",
        "ctl00$main$ddlShift": "1",
        "ctl00$main$ddlYear":  year,
        "ctl00$main$ddlMonth": month,
        "ctl00$main$btnView": "View"
    })

    r = session.post("http://192.168.200.26/digilog/MonthlyReport.aspx", data=payload)

    soup = BeautifulSoup(r.content, "html.parser")

    table = soup.find("table", {"class": "GridViewStyle"})
    if not table:
        pass

    trs = table.find_all("tr")
    cols = [td.get_text(strip=True) for td in trs[0].find_all(["td", "th"])]
    attendance_dict = {}


    for _, val in enumerate(trs[1:]):
        row = [td.get_text(strip=True) for td in val.find_all(["td", "th"])]
        if row[1] not in attendance_dict:
            attendance_dict[row[1]] = []
    
        date_index = cols[3:-3]
        val_index = row[3:-3]
        
        for i, _ in enumerate(date_index):
            d = {
                "employee_name": row[2],
                "date": f"{year}-{month}-{str(date_index[i]).zfill(2)}",
                "status": val_index[i]
            }
            
            attendance_dict[row[1]].append(d)

    return attendance_dict 



    

