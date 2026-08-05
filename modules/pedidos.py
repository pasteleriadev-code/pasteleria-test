import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_supabase_client

supabase = get_supabase_client()

def show_modulo_pedidos():
    st.header("🚀 Venta Rápida - POS & Encargos")

    # Botones superiores de acción general
    col_top1, col_top2 = st.columns([8, 2])
    with col_top2:
        if st.button("🧹 Limpiar Todo", use_container_width=True):
            st.session_state.carrito_pos = []
            st.session_state.cliente_pos = None
            st.rerun()

    # Pestaña desplegable de pendientes
    with st.expander("📂 VER VENTAS / PEDIDOS PENDIENTES", expanded=False):
        try:
            res_p = supabase.table("ventas").select("*, clientes(nombre_completo)").eq("estado", "Pendiente").order("fecha_entrega").execute()
            if res_p.data:
                df_pend = pd.DataFrame(res_p.data)
                df_pend["cliente"] = df_pend["clientes"].apply(lambda x: x["nombre_completo"] if x else "N/A")
                
                st.dataframe(
                    df_pend[["fecha_entrega", "cliente", "forma_entrega", "monto_total", "monto_pagado", "observaciones"]],
                    column_config={
                        "fecha_entrega": "Entrega",
                        "cliente": "Cliente",
                        "forma_entrega": "Modo",
                        "monto_total": st.column_config.NumberColumn("Total", format="$%.2f"),
                        "monto_pagado": st.column_config.NumberColumn("Seña/Pagado", format="$%.2f"),
                        "observaciones": "Notas"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay pedidos pendientes.")
        except Exception as e:
            st.error(f"Error al cargar pendientes: {e}")

    st.markdown("---")

    # ---------------------------------------------------------
    # 1. ENCABEZADO: CLIENTE Y VENDEDOR (Exacto a tu 1ra imagen)
    # ---------------------------------------------------------
    res_c = supabase.table("clientes").select("*").order("nombre_completo").execute()
    clientes = res_c.data or []
    dict_clientes = {f"{c['nombre_completo']} ({c.get('telefono','')})": c for c in clientes}

    c_cli, c_btn_cli, c_vend = st.columns([6, 1, 3])
    
    cli_sel = c_cli.selectbox(
        "🪪 Buscar Cliente (Nombre, Apellido, Teléfono o Razón Social)",
        options=list(dict_clientes.keys())
    )
    cliente_actual = dict_clientes[cli_sel] if cli_sel else None

    # Modal rápido para agregar cliente si no existe
    with c_btn_cli:
        st.write("") # Espaciador vertical
        if st.button("➕", help="Agregar Nuevo Cliente"):
            st.session_state.mostrar_form_cliente = True

    if st.session_state.get("mostrar_form_cliente", False):
        with st.form("form_quick_cliente"):
            st.subheader("Nuevo Cliente Rápidamente")
            n_nombre = st.text_input("Nombre Completo *")
            n_tel = st.text_input("Teléfono")
            n_dir = st.text_input("Dirección")
            if st.form_submit_button("Guardar"):
                if n_nombre.strip():
                    supabase.table("clientes").insert({"nombre_completo": n_nombre, "telefono": n_tel, "direccion": n_dir}).execute()
                    st.session_state.mostrar_form_cliente = False
                    st.success("Cliente guardado.")
                    st.rerun()

    vendedor = c_vend.selectbox("👔 Vendedor", ["Martin Yazlle", "Caja Mostrador", "Atención WhatsApp"])

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. AÑADIR PRODUCTOS AL CARRITO (Exacto a tu 1ra imagen)
    # ---------------------------------------------------------
    st.subheader("🔍 Añadir Productos")
    
    res_prod = supabase.table("productos").select("*").eq("activo", True).order("nombre").execute()
    productos = res_prod.data or []
    dict_productos = {f"{p['nombre']} - ${p['precio_venta']:,.2f}": p for p in productos}

    if "carrito_pos" not in st.session_state:
        st.session_state.carrito_pos = []

    prod_sel_key = st.selectbox(
        "Buscar por nombre",
        options=["Escriba para buscar producto..."] + list(dict_productos.keys())
    )

    if prod_sel_key != "Escriba para buscar producto...":
        prod_obj = dict_productos[prod_sel_key]
        
        # Verificar si ya está en el carrito
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
        st.rerun()

    # ---------------------------------------------------------
    # 3. DETALLE DE LA VENTA (Exacto a tu 2da imagen)
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
            
            # Control de Cantidad (+ / -)
            nueva_cant = c_cant.number_input("Cant.", min_value=1, value=int(item["cantidad"]), key=f"cant_{idx}")
            item["cantidad"] = nueva_cant

            # Control de Precio (Permite cambiarlo en vivo si hay descuento)
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
    # 4. TOTAL A COBRAR & 5. FORMAS DE PAGO (Exacto a tu 2da imagen)
    # ---------------------------------------------------------
    st.markdown(f"## 💰 Total a Cobrar: **${total_a_cobrar:,.2f}**")

    st.subheader("💳 Formas de Pago")
    
    col_fp1, col_fp2 = st.columns([4, 4])
    metodo_pago = col_fp1.selectbox("Método 1", ["Efectivo", "Transferencia / MP", "Tarjeta de Débito", "Tarjeta de Crédito", "Cuenta Corriente"])
    monto_abonado = col_fp2.number_input("Monto Abonado / Seña ($)", min_value=0.0, value=float(total_a_cobrar), step=100.0, format="%.2f")

    diferencia = total_a_cobrar - monto_abonado
    if diferencia > 0:
        st.warning(f"⚠️ Faltan completar / Pendiente de cobro: **${diferencia:,.2f}**")
    elif diferencia < 0:
        st.info(f"💡 Vuelto a entregar: **${abs(diferencia):,.2f}**")

    st.markdown("---")

    # ---------------------------------------------------------
    # 6. FORMA DE ENTREGA (Exacto a tu 2da imagen)
    # ---------------------------------------------------------
    st.subheader("🚚 Forma de Entrega")

    c_ent1, c_ent2 = st.columns([4, 4])
    forma_entrega = c_ent1.radio("¿Cómo se entrega?", ["Mostrador", "Reparto / Envíos"], horizontal=False)
    fecha_entrega = c_ent2.date_input("Fecha de entrega", value=datetime.today())

    observaciones = st.text_input(
        "📝 Observaciones / Notas para el Repartidor o Pastelero",
        placeholder="Ej: Pasar antes de las 16hs, dedicatoria 'Feliz Cumple Lucas', cobro exacto..."
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # 7. BOTONES DE ACCIÓN (FINALIZAR vs GUARDAR PENDIENTES)
    # ---------------------------------------------------------
    c_btn_fin, c_btn_pend = st.columns(2)

    # Botón Principal: Finalizar Venta
    if c_btn_fin.button("🏁 FINALIZAR Y REGISTRAR VENTA", type="primary", use_container_width=True, disabled=len(st.session_state.carrito_pos) == 0):
        try:
            # 1. Registrar venta como Finalizada
            payload_v = {
                "cliente_id": cliente_actual["id"],
                "vendedor": vendedor,
                "monto_total": total_a_cobrar,
                "monto_pagado": monto_abonado,
                "metodo_pago": metodo_pago,
                "forma_entrega": forma_entrega,
                "fecha_entrega": str(fecha_entrega),
                "observaciones": observaciones,
                "estado": "Finalizada"
            }
            res_v = supabase.table("ventas").insert(payload_v).execute()
            venta_id = res_v.data[0]["id"]

            # 2. Insertar Detalle
            for item in st.session_state.carrito_pos:
                supabase.table("venta_detalles").insert({
                    "venta_id": venta_id,
                    "producto_id": item["id"],
                    "cantidad": item["cantidad"],
                    "precio_unitario": item["precio"]
                }).execute()

            st.success("🎉 ¡Venta registrada exitosamente!")
            st.session_state.carrito_pos = []
            st.rerun()
        except Exception as e:
            st.error(f"Error al registrar la venta: {e}")

    # Botón Secundario: Guardar como Pendiente (Encargo)
    if c_btn_pend.button("⏳ GUARDAR COMO PENDIENTES / ENCARGO", use_container_width=True, disabled=len(st.session_state.carrito_pos) == 0):
        try:
            payload_v = {
                "cliente_id": cliente_actual["id"],
                "vendedor": vendedor,
                "monto_total": total_a_cobrar,
                "monto_pagado": monto_abonado,
                "metodo_pago": metodo_pago,
                "forma_entrega": forma_entrega,
                "fecha_entrega": str(fecha_entrega),
                "observaciones": observaciones,
                "estado": "Pendiente"
            }
            res_v = supabase.table("ventas").insert(payload_v).execute()
            venta_id = res_v.data[0]["id"]

            for item in st.session_state.carrito_pos:
                supabase.table("venta_detalles").insert({
                    "venta_id": venta_id,
                    "producto_id": item["id"],
                    "cantidad": item["cantidad"],
                    "precio_unitario": item["precio"]
                }).execute()

            st.success("🎉 ¡Pedido guardado como PENDIENTE! Aparecerá en el panel de encargos.")
            st.session_state.carrito_pos = []
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar encargo: {e}")
