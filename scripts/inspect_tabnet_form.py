"""Inspeciona, sem submeter, o contrato HTML de um formulário TabNet."""

import sys

import httpx
from bs4 import BeautifulSoup


def main(url: str) -> None:
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "lxml")
    for name in ("Linha", "Coluna", "Incremento", "PAno"):
        select = soup.find("select", attrs={"name": name})
        options = [
            (option.get("value"), option.get_text(" ", strip=True), option.has_attr("selected"))
            for option in select.find_all("option")
        ]
        print(name, options)
    inputs = [
        (item.get("name"), item.get("value"), item.get("checked"))
        for item in soup.find_all("input")
        if item.get("name")
    ]
    print("inputs", inputs)


if __name__ == "__main__":
    main(sys.argv[1])
