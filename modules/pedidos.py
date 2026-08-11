import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_pedidos():
    st.header("🚀 Venta Rápida - POS & Encargos")

    # Botón superior de limpieza
    col_top1, col_top2 = st.columns([8, 2])
    with col_top2:
        if st.button("🧹 Limpiar Todo", use_container_width=True):
            st.session_state.carrito_pos = []
            st.rerun()

    # ---------------------------------------------------------
    # 0. PESTAÑA DESPLEGABLE: ENCARGOS PENDIENTES
    # ---------------------------------------------------------
    with st.expander("📂 VER PEDIDOS / ENCARGOS PENDIENTES", expanded=False):
        try:
            # Consulta de pedidos pendientes (excluyendo 'Entregado')
            res_p = supabase.table("pedidos").select("*").neq("estado", "Entregado").order("fecha_entrega").execute()
            res_c_all = supabase.table("clientes").select("id, nombre").execute()
            
            pedidos_list = res_p.data or []
            dict_map_clientes = {c["id"]: c["nombre"] for c in (res_c_all.data or [])}

            if pedidos_list:
                df_pend = pd.DataFrame(pedidos_list)
                df_pend["cliente"] = df_pend["cliente_id"].map(dict_map_clientes).fillna("N/A")
                
                # Asegurar columnas opcionales si vienen nulas
                for col in ["forma_entrega", "monto_sena", "notas_personalizacion"]:
                    if col not in df_pend.columns:
                        df_pend[col] = "-"

                st.dataframe(
                    df_pend[["fecha_entrega", "cliente", "forma_entrega", "monto_total", "monto_sena", "estado", "notas_personalizacion"]],
                    column_config={
                        "fecha_entrega": "Entrega",
                        "cliente": "Cliente",
                        "forma_entrega": "Modo",
                        "monto_total": st.column_config.NumberColumn("Total ($)", format="$%.2f"),
                        "monto_sena": st.column_config.NumberColumn("Seña ($)", format="$%.2f"),
                        "estado": "Estado",
                        "notas_personalizacion": "Notas / Dedicatoria"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay encargos pendientes de entrega.")
        except Exception as e:
            st.error(f"Error al cargar pedidos pendientes: {e}")

    st.markdown("---")

    # ---------------------------------------------------------
    # 1. ENCABEZADO: SELECCIÓN O CREACIÓN DE CLIENTE
    # ---------------------------------------------------------
    try:
        res_c = supabase.table("clientes").select("*").order("nombre").execute()
        clientes = res_c.data or []
    except Exception as e:
        st.error(f"Error al cargar lista de clientes: {e}")
        clientes = []

    dict_clientes = {f"{c['nombre']} ({c.get('telefono','') or 'Sin Tel.'})": c for c in clientes}

    c_cli, c_btn_cli, c_vend = st.columns([6, 1, 3])
    
    if dict_clientes:
        cli_sel = c_cli.selectbox(
            "🪪 Buscar Cliente (Nombre, Apellido o Teléfono)",
            options=list(dict_clientes.keys())
        )
        cliente_actual = dict_clientes[cli_sel] if cli_sel else None
    else:
        c_cli.warning("No hay clientes registrados en el sistema.")
        cliente_actual = None

    # Modal para dar de alta clientes rápidamente
    with c_btn_cli:
        st.write("") 
        if st.button("➕", help="Crear Nuevo Cliente"):
            st.session_state.mostrar_form_cliente_pos = not st.session_state.get("mostrar_form_cliente_pos", False)

    if st.session_state.get("mostrar_form_cliente_pos", False):
        with st.form("form_quick_cliente_pos"):
            st.subheader("➕ Nuevo Cliente Rápido")
            col_fa, col_fb = st.columns(2)
            n_nombre = col_fa.text_input("Nombre Completo *")
            n_tel = col_fb.text_input("Teléfono")
            col_fc, col_fd = st.columns(2)
            n_email = col_fc.text_input("Email")
            n_dir = col_fd.text_input("Dirección")
            
            if st.form_submit_button("Guardar Cliente"):
                if n_nombre.strip():
                    supabase.table("clientes").insert({
                        "nombre": n_nombre.strip(), 
                        "telefono": n_tel, 
                        "email": n_email, 
                        "direccion": n_dir
                    }).execute()
                    st.session_state.mostrar_form_cliente_pos = False
                    st.success("Cliente guardado exitosamente.")
                    st.rerun()
                else:
                    st.error("El nombre del cliente es obligatorio.")

    vendedor = c_vend.selectbox("👔 Vendedor", ["Martin Yazlle", "Caja Mostrador", "Atención WhatsApp"])

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. AÑADIR PRODUCTOS DEL CATÁLOGO AL CARRITO
    # ---------------------------------------------------------
    st.subheader("🔍 Añadir Productos")
    
    try:
        res_prod = supabase.table("productos").select("*").eq("activo", True).order("nombre").execute()
        productos = res_prod.data or []
    except Exception as e:
        productos = []
        st.error(f"Error al cargar catálogo de productos: {e}")

    dict_productos = {f"{p['nombre']} - ${float(p['precio_venta']):,.2f}": p for p in productos}

    if "carrito_pos" not in st.session_state:
        st.session_state.carrito_pos = []

    def agregar_producto_al_carrito():
        prod_sel_key = st.session_state.get("selector_producto_pos")
        if prod_sel_key and prod_sel_key != "Escriba para buscar producto...":
            if prod_sel_key in dict_productos:
                prod_obj = dict_productos[prod_sel_key]
                
                existe = next((item for item in st.session_state.carrito_pos if item["id"] == prod_obj["id"]), None)
                if existe:
                    existe["cantidad"] += 1
                else:
                    st.session_state.carrito_pos.append({
                        "id": prod_obj["id"],
                        "nombre": prod_obj["nombre"],
                        "precio": float(prod_obj["precio_venta"]),
                        "cantidad": 1
                    })
            st.session_state["selector_producto_pos"] = "Escriba para buscar producto..."

    st.selectbox(
        "Buscar por nombre en el catálogo",
        options=["Escriba para buscar producto..."] + list(dict_productos.keys()),
        key="selector_producto_pos",
        on_change=agregar_producto_al_carrito
    )

    # ---------------------------------------------------------
    # 3. DETALLE DE LA VENTA / TABLA INTERACTIVA
    # ---------------------------------------------------------
    st.subheader("🛒 Detalle de la Venta")

    if not st.session_state.carrito_pos:
        st.info("El carrito está vacío.")
        total_a_cobrar = 0.0
    else:
        total_a_cobrar = 0.0
        
        for idx, item in enumerate(st.session_state.carrito_pos):
            c_nom, c_cant, c_prec, c_sub, c_del = st.columns([4, 2, 2, 2, 1])
            
            c_nom.markdown(f"**{item['nombre']}**")
            
            nueva_cant = c_cant.number_input("Cant.", min_value=1, value=int(item["cantidad"]), key=f"cant_{idx}")
            item["cantidad"] = nueva_cant

            nuevo_precio = c_prec.number_input("Precio", min_value=0.0, value=float(item["precio"]), step=50.0, format="%.2f", key=f"prec_{idx}")
            item["precio"] = nuevo_precio

            subtotal_item = item["cantidad"] * item["precio"]
            total_a_cobrar += subtotal_item

            c_sub.markdown(f"**Sub: ${subtotal_item:,.2f}**")
            
            if c_del.button("🗑️", key=f"del_{idx}"):
                st.session_state.carrito_pos.pop(idx)
                st.rerun()

        st.markdown("---")

    # ---------------------------------------------------------
    # 4. TOTAL A COBRAR & 5. FORMAS DE PAGO / SEÑA
    # ---------------------------------------------------------
    st.markdown(f"## 💰 Total a Cobrar: **${total_a_cobrar:,.2f}**")

    st.subheader("💳 Formas de Pago")
    
    col_fp1, col_fp2 = st.columns(2)
    metodo_pago = col_fp1.selectbox("Método de Pago", ["Efectivo", "Transferencia / MercadoPago", "Tarjeta de Débito", "Tarjeta de Crédito", "Cuenta Corriente"])
    monto_abonado = col_fp2.number_input("Monto Abonado / Seña ($)", min_value=0.0, value=float(total_a_cobrar), step=100.0, format="%.2f")

    diferencia = total_a_cobrar - monto_abonado
    if diferencia > 0:
        st.warning(f"⚠️ Faltan completar / Restan abonar: **${diferencia:,.2f}**")
    elif diferencia < 0:
        st.info(f"💡 Vuelto a entregar: **${abs(diferencia):,.2f}**")

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. FORMA DE ENTREGA & NOTAS
    # ---------------------------------------------------------
    st.subheader("🚚 Forma de Entrega")

    c_ent1, c_ent2 = st.columns(2)
    forma_entrega = c_ent1.radio("¿Cómo se entrega?", ["Mostrador", "Reparto / Envíos"], horizontal=False)
    fecha_entrega = c_ent2.date_input("Fecha de entrega", value=datetime.today())

    observaciones = st.text_input(
        "📝 Observaciones / Notas de Personalización",
        placeholder="Ej: Relleno de dulce de leche con nuez, dedicatoria 'Feliz Cumple', horario especial..."
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # 7. BOTONES DE GUARDADO (FINALIZAR VS PENDIENTE)
    # ---------------------------------------------------------
    c_btn_fin, c_btn_pend = st.columns(2)

    # A) Finalizar y Registrar Venta Directa
    if c_btn_fin.button("🏁 FINALIZAR Y REGISTRAR VENTA", type="primary", use_container_width=True, disabled=len(st.session_state.carrito_pos) == 0):
        if not cliente_actual:
            st.error("Por favor selecciona un cliente antes de guardar.")
        else:
            try:
                # 1. Crear el registro en la tabla pedidos
                payload_p = {
                    "cliente_id": cliente_actual["id"],
                    "vendedor": vendedor,
                    "monto_total": total_a_cobrar,
                    "monto_sena": monto_abonado,
                    "metodo_pago": metodo_pago,
                    "forma_entrega": forma_entrega,
                    "fecha_pedido": datetime.now().isoformat(),
                    "fecha_entrega": str(fecha_entrega),
                    "notas_personalizacion": observaciones,
                    "estado": "Entregado"
                }
                res_p = supabase.table("pedidos").insert(payload_p).execute()
                pedido_id = res_p.data[0]["id"]

                detalles_payload = []
                for item in st.session_state.carrito_pos:
                    subtotal_prod = float(item["cantidad"] * item["precio"])
                    
                    # Estructura del detalle
                    detalles_payload.append({
                        "pedido_id": pedido_id,
                        "producto_id": item["id"],
                        "cantidad": int(item["cantidad"]),
                        "precio_unitario": item["precio"],
                        "subtotal": subtotal_prod
                    })
                    
                    # 2. DESCONTAR STOCK USANDO 'stock_actual'
                    res_prod_curr = supabase.table("productos").select("stock_actual").eq("id", item["id"]).execute()
                    if res_prod_curr.data:
                        stock_previo = res_prod_curr.data[0].get("stock_actual", 0) or 0
                        nuevo_stock = max(0, stock_previo - int(item["cantidad"]))
                        supabase.table("productos").update({"stock_actual": nuevo_stock}).eq("id", item["id"]).execute()

                # 3. Guardar detalles
                supabase.table("pedido_detalles").insert(detalles_payload).execute()

                st.success("🎉 ¡Venta finalizada, registrada y stock actualizado correctamente!")
                st.session_state.carrito_pos = []
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar venta: {e}")

    # B) Guardar como Pendiente / Encargo
    if c_btn_pend.button("⏳ GUARDAR COMO PENDIENTES / ENCARGO", use_container_width=True, disabled=len(st.session_state.carrito_pos) == 0):
        if not cliente_actual:
            st.error("Por favor selecciona un cliente antes de guardar.")
        else:
            try:
                payload_p = {
                    "cliente_id": cliente_actual["id"],
                    "vendedor": vendedor,
                    "monto_total": total_a_cobrar,
                    "monto_sena": monto_abonado,
                    "metodo_pago": metodo_pago,
                    "forma_entrega": forma_entrega,
                    "fecha_pedido": datetime.now().isoformat(),
                    "fecha_entrega": str(fecha_entrega),
                    "notas_personalizacion": observaciones,
                    "estado": "Pendiente"
                }
                res_p = supabase.table("pedidos").insert(payload_p).execute()
                pedido_id = res_p.data[0]["id"]

                detalles_payload = [
                    {
                        "pedido_id": pedido_id,
                        "producto_id": item["id"],
                        "cantidad": int(item["cantidad"]),
                        "precio_unitario": item["precio"],
                        "subtotal": float(item["cantidad"] * item["precio"])
                    }
                    for item in st.session_state.carrito_pos
                ]
                
                supabase.table("pedido_detalles").insert(detalles_payload).execute()

                st.success("🎉 ¡Encargo guardado como PENDIENTE! Puedes verlo en la lista superior.")
                st.session_state.carrito_pos = []
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar encargo: {e}")
