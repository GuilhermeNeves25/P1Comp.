from flask import Flask, render_template, request, redirect, url_for
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient
import uuid
from datetime import datetime

app = Flask(__name__)

# --- CONEXÃO AZURE (SUA CHAVE) ---
AZURE_CS = "DefaultEndpointsProtocol=https;AccountName=stocompnuvem2p1;AccountKey=ft6foTxIotQ3Bb7LWamtHK9B/ZWZqt+yeE+Zefpw/rZZ3hAqoMO0E/ciRe58povuHLd84YUc8Urb+ASt92dYSA==;EndpointSuffix=core.windows.net"

table_service = TableServiceClient.from_connection_string(conn_str=AZURE_CS)
blob_service = BlobServiceClient.from_connection_string(conn_str=AZURE_CS)

# Criando Tabelas e Container de fotos se não existirem
for table in ["Produtos", "Clientes", "Pedidos"]:
    try:
        table_service.create_table_if_not_exists(table_name=table)
    except: pass

try:
    container_client = blob_service.get_container_client("fotos-produtos")
    if not container_client.exists():
        container_client.create_container(public_access="blob")
except: pass

tb_produtos = table_service.get_table_client("Produtos")
tb_clientes = table_service.get_table_client("Clientes")
tb_pedidos = table_service.get_table_client("Pedidos")

# --- ROTAS PRINCIPAIS ---
@app.route('/')
def index():
    produtos = list(tb_produtos.query_entities("PartitionKey eq 'Produto'"))
    clientes = list(tb_clientes.query_entities("PartitionKey eq 'Cliente'"))
    return render_template('index.html', produtos=produtos, clientes=clientes)

@app.route('/add_produto', methods=['POST'])
def add_produto():
    id_prod = str(uuid.uuid4())
    foto = request.files['foto']
    url_foto = ""
    
    if foto: 
        blob_client = blob_service.get_blob_client(container="fotos-produtos", blob=id_prod + foto.filename)
        blob_client.upload_blob(foto.read(), overwrite=True)
        url_foto = blob_client.url

    produto = {
        "PartitionKey": "Produto", "RowKey": id_prod,
        "Marca": request.form['marca'], "Modelo": request.form['modelo'],
        "Valor": request.form['valor'], "Quantidade": request.form['quantidade'],
        "FotoUrl": url_foto
    }
    tb_produtos.create_entity(entity=produto)
    return redirect(url_for('index'))

@app.route('/delete_produto/<id>')
def delete_produto(id):
    tb_produtos.delete_entity(partition_key="Produto", row_key=id)
    return redirect(url_for('index'))

@app.route('/add_cliente', methods=['POST'])
def add_cliente():
    cliente = {
        "PartitionKey": "Cliente", "RowKey": str(uuid.uuid4()),
        "Nome": request.form['nome'], "Email": request.form['email'], "Telefone": request.form['telefone']
    }
    tb_clientes.create_entity(entity=cliente)
    return redirect(url_for('index'))

@app.route('/delete_cliente/<id>')
def delete_cliente(id):
    tb_clientes.delete_entity(partition_key="Cliente", row_key=id)
    return redirect(url_for('index'))

@app.route('/checkout/<produto_id>', methods=['GET', 'POST'])
def checkout(produto_id):
    produto = tb_produtos.get_entity(partition_key="Produto", row_key=produto_id)
    clientes = list(tb_clientes.query_entities("PartitionKey eq 'Cliente'"))
    
    if request.method == 'POST':
        pedido = {
            "PartitionKey": "Pedido", "RowKey": str(uuid.uuid4()),
            "ClienteId": request.form['cliente_id'],
            "ProdutoModelo": produto['Modelo'],
            "ValorTotal": produto['Valor'],
            "Pagamento": request.form['pagamento'],
            "Entrega": request.form['entrega'],
            "Data": str(datetime.now().date())
        }
        tb_pedidos.create_entity(entity=pedido)
        return f"<h3>Pedido concluido!</h3><a href='/'>Voltar para a loja</a>"
        
    return render_template('checkout.html', produto=produto, clientes=clientes)

@app.route('/area_cliente/<cliente_id>')
def area_cliente(cliente_id):
    cliente = tb_clientes.get_entity(partition_key="Cliente", row_key=cliente_id)
    pedidos = list(tb_pedidos.query_entities(f"PartitionKey eq 'Pedido' and ClienteId eq '{cliente_id}'"))
    return render_template('area_cliente.html', cliente=cliente, pedidos=pedidos)

if __name__ == '__main__':
    app.run(debug=True)