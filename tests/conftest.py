import pytest

from sweet.compiler import Session

SALES = """customer,region,quantity,price
alice,north,2,1500
bob,south,1,300
carol,north,5,120
dave,east,3,2500
erin,south,4,80
frank,east,1,1000
gina,west,2,1001
henry,north,1,50
"""
CUSTOMERS = "customer_id,name,city\n1,Asha,Mumbai\n2,Ben,Pune\n3,Chen,Nashik\n"
ORDERS = "order_id,customer_id,amount\n10,1,500\n11,2,250\n12,4,900\n13,1,75\n"


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "sales.csv").write_text(SALES)
    (tmp_path / "customers.csv").write_text(CUSTOMERS)
    (tmp_path / "orders.csv").write_text(ORDERS)
    return tmp_path


@pytest.fixture
def session(data_dir):
    return Session(base_dir=data_dir, output_dir=data_dir / "out")
