import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_supabase_client

supabase = get_supabase_client()

def normalizar_unidad(u: str) -> str:
    """Normaliza el texto de las unidades de medida para comparaciones."""
    if not u:
        return ""
    u_clean = u.lower().strip()
    if u_clean in ["kg", "kilo", "kilogramo", "kilogramos", "kgs"]:
        return "kg"
    if u_clean in ["g", "gramo", "gramos", "gr", "grs"]:
        return "g"
    if u_clean in ["l", "lt", "litro", "litros", "lts"]:
        return "l"
    if u_clean in ["ml", "mililitro", "mililitros", "cc"]:
        return "ml"
    if u_clean in ["unid", "unidad", "unidades", "u"]:
        return "u"
    return u_clean

def obtener_factor_conversion_defecto(u_compra: str, u_base: str) -> float:
    """Retorna el factor multiplicador por defecto para pasar de unidad de compra a unidad base."""
    compra_norm = normalizar_unidad(u_compra)
    base_norm = normalizar_unidad(u_base)

    if compra_norm == base_norm:
        return 1.0

    # Conversiones de Peso
    if compra_norm == "kg" and base_norm == "g":
        return 1000.0
    if compra_norm == "g" and base_norm == "kg":
        return 0.001

    # Conversiones de Volumen
    if compra_norm == "l" and base_norm == "ml":
        return 1000.0
    if compra_norm == "ml" and base_norm == "l":
        return 0.001

    return 1.0

def show_modulo_proveedores():
    st.header("🚚 Gestión de Proveedores y Compras")

    tab_explorador, tab_nuevo, tab_modificar, tab_compras = st.tabs([
        "🔍 Explorador", 
        "➕ Nuevo Proveedor", 
        "✏️ Modificar", 
        "🛒 Cargar / Historial Compras"
    ])

    # ---------------------------------------------------------
    # 1. EXPLORADOR DE PROVEEDORES
    # ---------------------------------------------------------
    with tab_explorador:
        st.subheader("Proveedores Registrados")
        try:
            res = supabase.table("proveedores").select("*").order("razon_social").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                cols_deseadas = ["razon_social", "cuit", "telefono", "condicion_fiscal", "direccion", "rubros"]
                cols_existentes = [c for c in cols_deseadas if c in df.columns]
                
                st.dataframe(
                    df[cols_existentes],
                    column_config={
                        "razon_social": "Razón Social",
                        "cuit": "CUIT",
                        "telefono": "Teléfono",
                        "condicion_fiscal": "Condición Fiscal",
                        "direccion": "Dirección",
                        "rubros": "Rubros"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay proveedores dados de alta.")
        except Exception as e:
            st.error(f"Error al cargar proveedores: {e}")

    # ---------------------------------------------------------
    # 2. ALTA DE PROVEEDORES
    # ---------------------------------------------------------
    with tab_nuevo:
        st.info("💡 Completá los datos del nuevo proveedor")
        
        with st.form("form_nuevo_proveedor", clear_on_submit=True):
            col1, col2 = st.columns(2)
            razon_social = col1.text_input("Razón Social *")
            telefono = col2.text_input("Teléfono")

            col3, col4 = st.columns(2)
            cuit = col3.text_input("CUIT (Formato: XX-XXXXXXXX-X)")
            condicion_fiscal = col4.selectbox(
                "Condición Fiscal", 
                ["Responsable Inscripto", "Monotributo", "Exento", "Consumidor Final"]
            )

            direccion = st.text_input("Dirección")
            rubros = st.text_input("Asociar Rubros", placeholder="Ej. Lácteos, Harinas, Empaques")

            submitted = st.form_submit_button("Guardar Proveedor", use_container_width=True)

            if submitted:
                if not razon_social.strip():
                    st.error("La Razón Social es obligatoria.")
                else:
                    nuevo_prov = {
                        "razon_social": razon_social.strip(),
                        "cuit": cuit.strip(),
                        "telefono": telefono.strip(),
                        "condicion_fiscal": condicion_fiscal,
                        "direccion": direccion.strip(),
                        "rubros": rubros.strip()
                    }
                    try:
                        supabase.table("proveedores").insert(nuevo_prov).execute()
                        st.success(f"¡Proveedor '{razon_social}' registrado exitosamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar proveedor: {e}")

    # ---------------------------------------------------------
    # 3. MODIFICAR PROVEEDORES
    # ---------------------------------------------------------
    with tab_modificar:
        st.subheader("Editar Proveedor Existente")
        try:
            res_prov = supabase.table("proveedores").select("*").order("razon_social").execute()
            listado_provs = res_prov.data

            if listado_provs:
                dict_provs = {p["razon_social"]: p for p in listado_provs}
                prov_seleccionado = st.selectbox("Seleccionar Proveedor a Modificar:", list(dict_provs.keys()))
                
                datos_actuales = dict_provs[prov_seleccionado]

                with st.form("form_edit_proveedor"):
                    col1, col2 = st.columns(2)
                    edit_razon = col1.text_input("Razón Social", value=datos_actuales.get("razon_social", ""))
                    edit_tel = col2.text_input("Teléfono", value=datos_actuales.get("telefono", ""))

                    col3, col4 = st.columns(2)
                    edit_cuit = col3.text_input("CUIT", value=datos_actuales.get("cuit", ""))
                    
                    opciones_cf = ["Responsable Inscripto", "Monotributo", "Exento", "Consumidor Final"]
                    cf_actual = datos_actuales.get("condicion_fiscal", "Responsable Inscripto")
                    idx_cf = opciones_cf.index(cf_actual) if cf_actual in opciones_cf else 0
                    edit_cf = col4.selectbox("Condición Fiscal", opciones_cf, index=idx_cf)

                    edit_dir = st.text_input("Dirección", value=datos_actuales.get("direccion", ""))
                    edit_rubros = st.text_input("Rubros", value=datos_actuales.get("rubros", ""))

                    if st.form_submit_button("Actualizar Cambios", use_container_width=True):
                        update_data = {
                            "razon_social": edit_razon.strip(),
                            "cuit": edit_cuit.strip(),
                            "telefono": edit_tel.strip(),
                            "condicion_fiscal": edit_cf,
                            "direccion": edit_dir.strip(),
                            "rubros": edit_rubros.strip()
                        }
                        supabase.table("proveedores").update(update_data).eq("id", datos_actuales["id"]).execute()
                        st.success("¡Datos actualizados correctamente!")
                        st.rerun()
            else:
                st.info("No hay proveedores disponibles para editar.")
        except Exception as e:
            st.error(f"Error al modificar proveedor: {e}")

    # ---------------------------------------------------------
    # 4. CARGAR COMPRAS E HISTORIAL CON EQUIVALENCIAS
    # ---------------------------------------------------------
    with tab_compras:
        with st.expander("📁 Ver / Ocultar Historial de Compras", expanded=False):
            try:
                historial = supabase.table("compras").select("*, proveedores(razon_social)").order("fecha_factura", ascending=False).execute()
                if historial.data:
                    df_h = pd.DataFrame(historial.data)
                    df_h["proveedor"] = df_h["proveedores"].apply(lambda x: x["razon_social"] if isinstance(x, dict) and "razon_social" in x else "N/A")
                    
                    cols_historial = ["fecha_factura", "proveedor", "punto_venta", "numero_factura", "metodo_pago", "monto_total"]
                    cols_h_existentes = [c for c in cols_historial if c in df_h.columns]

                    st.dataframe(
                        df_h[cols_h_existentes],
                        column_config={
                            "fecha_factura": "Fecha",
                            "proveedor": "Proveedor",
                            "punto_venta": "Punto Venta",
                            "numero_factura": "N° Factura",
                            "metodo_pago": "Método Pago",
                            "monto_total": st.column_config.NumberColumn("Monto Total", format="$%.2f")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No hay compras registradas aún.")
            except Exception as e:
                st.error(f"Error al cargar historial de compras: {e}")

        st.subheader("📄 Datos de la Factura Actual")

        res_p = supabase.table("proveedores").select("id, razon_social").execute()
        provs = res_p.data

        if not provs:
            st.warning("⚠️ Primero debes dar de alta al menos un Proveedor en la pestaña 'Nuevo Proveedor'.")
            return

        dict_provs_compra = {p["razon_social"]: p["id"] for p in provs}

        c1, c2, c3, c4 = st.columns([3, 1.5, 2, 2])
        prov_nombre = c1.selectbox("Proveedor", list(dict_provs_compra.keys()))
        pv = c2.text_input("Punto Venta", value="00001", max_chars=5)
        nro_fac = c3.text_input("N° Factura", value="00000001", max_chars=8)
        metodo_pago = c4.selectbox("Método de Pago", ["Contado", "Transferencia", "Tarjeta Crédito/Débito", "Cuenta Corriente"])

        fecha_fac = st.date_input("Fecha de Factura", value=datetime.today())

        st.markdown("---")
        st.subheader("🔍 Añadir Insumo a la Compra (con Conversión de Unidades)")

        res_ins = supabase.table("insumos").select("*").order("nombre").execute()
        insumos = res_ins.data

        if not insumos:
            st.warning("⚠️ No hay insumos registrados en el inventario. Agrega insumos primero.")
            return

        dict_insumos = {i["nombre"]: i for i in insumos}

        if "carrito_compra" not in st.session_state:
            st.session_state.carrito_compra = []

        # Seleccionar el Insumo
        ins_sel_nombre = st.selectbox("Escriba para buscar producto/insumo...", list(dict_insumos.keys()))
        ins_objeto = dict_insumos[ins_sel_nombre]
        unidad_base = ins_objeto.get("unidad_medida", "unidades")

        st.caption(f"📏 **Unidad base en sistema para {ins_objeto['nombre']}:** `{unidad_base}`")

        # Configuración de la compra (Unidad de factura vs Unidad base)
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
        
        cant_factura = col_f1.number_input("Cantidad en Factura", min_value=0.01, value=1.00, step=0.5)
        
        opciones_unidades = list(set([unidad_base, "kg", "g", "l", "ml", "unidades", "paquete/caja/bolsa"]))
        idx_default_u = opciones_unidades.index("kg") if "kg" in opciones_unidades and normalizar_unidad(unidad_base) == "g" else 0
        
        unidad_factura = col_f2.selectbox("Unidad en Factura", opciones_unidades, index=idx_default_u)
        
        tipo_precio = col_f3.selectbox("Modalidad de Precio", ["Precio Total del Item ($)", "Precio Unitario Factura ($)"])
        monto_ingresado = col_f4.number_input("Monto ($)", min_value=0.0, value=0.0, step=10.0, format="%.2f")

        # Conversión / Equivalencia
        factor_sugerido = obtener_factor_conversion_defecto(unidad_factura, unidad_base)
        
        col_eq1, col_eq2 = st.columns([3, 3])
        factor_conversion = col_eq1.number_input(
            f"Equivalencia: ¿Cuántas [{unidad_base}] contiene 1 [{unidad_factura}]?", 
            min_value=0.0001, 
            value=float(factor_sugerido),
            format="%.4f"
        )

        # Cálculos en tiempo real
        cant_base_calculada = float(cant_factura) * float(factor_conversion)
        
        if tipo_precio == "Precio Total del Item ($)":
            subtotal_item = float(monto_ingresado)
        else:
            subtotal_item = float(cant_factura) * float(monto_ingresado)

        costo_unitario_base = (subtotal_item / cant_base_calculada) if cant_base_calculada > 0 else 0.0

        # Vista previa de la conversión
        st.info(
            f"📊 **Vista Previa de Ingreso:**\n"
            f"- **Se sumará al Stock:** `{cant_base_calculada:,.2f} {unidad_base}`\n"
            f"- **Costo calculado por unidad base:** `${costo_unitario_base:,.4f} / {unidad_base}`\n"
            f"- **Subtotal de la fila:** `${subtotal_item:,.2f}`"
        )

        if st.button("➕ Agregar Item al Carrito", use_container_width=True):
            if subtotal_item <= 0:
                st.warning("⚠️ El monto asignado debe ser mayor a 0.")
            else:
                st.session_state.carrito_compra.append({
                    "insumo_id": ins_objeto["id"],
                    "nombre": ins_objeto["nombre"],
                    "cant_factura": float(cant_factura),
                    "unidad_factura": unidad_factura,
                    "cant_base": cant_base_calculada,
                    "unidad_base": unidad_base,
                    "costo_unitario_base": costo_unitario_base,
                    "subtotal": subtotal_item
                })
                st.rerun()

        # ---------------------------------------------------------
        # CARRITO Y CONFIRMACIÓN
        # ---------------------------------------------------------
        if st.session_state.carrito_compra:
            st.markdown("### 🛒 Detalle de la Compra a Registrar")
            df_carrito = pd.DataFrame(st.session_state.carrito_compra)
            
            # Formateo visual para la tabla
            df_carrito["factura_detalle"] = df_carrito.apply(lambda r: f"{r['cant_factura']} {r['unidad_factura']}", axis=1)
            df_carrito["stock_detalle"] = df_carrito.apply(lambda r: f"{r['cant_base']:,.2f} {r['unidad_base']}", axis=1)

            st.dataframe(
                df_carrito[["nombre", "factura_detalle", "stock_detalle", "costo_unitario_base", "subtotal"]],
                column_config={
                    "nombre": "Insumo",
                    "factura_detalle": "Factura (Cant / Unidad)",
                    "stock_detalle": "Ingreso a Stock (Base)",
                    "costo_unitario_base": st.column_config.NumberColumn("Costo Base Unitario", format="$%.4f"),
                    "subtotal": st.column_config.NumberColumn("Subtotal", format="$%.2f")
                },
                use_container_width=True, 
                hide_index=True
            )

            total_compra = df_carrito["subtotal"].sum()
            st.markdown(f"### **Total Factura: ${total_compra:,.2f}**")

            col_cancel, col_confirm = st.columns(2)
            if col_cancel.button("❌ Vaciar Carrito", use_container_width=True):
                st.session_state.carrito_compra = []
                st.rerun()

            if col_confirm.button("✅ Registrar Factura y Actualizar Stock", type="primary", use_container_width=True):
                try:
                    compra_payload = {
                        "proveedor_id": dict_provs_compra[prov_nombre],
                        "punto_venta": pv,
                        "numero_factura": nro_fac,
                        "fecha_factura": str(fecha_fac),
                        "metodo_pago": metodo_pago,
                        "monto_total": float(total_compra)
                    }
                    compra_res = supabase.table("compras").insert(compra_payload).execute()
                    compra_id = compra_res.data[0]["id"]

                    for item in st.session_state.carrito_compra:
                        # Registro en el detalle de compras en unidades base
                        detalle_payload = {
                            "compra_id": compra_id,
                            "insumo_id": item["insumo_id"],
                            "cantidad": item["cant_base"],
                            "precio_unitario": item["costo_unitario_base"]
                        }
                        supabase.table("compra_detalles").insert(detalle_payload).execute()

                        # Actualización de stock y costo del insumo
                        ins_id = item["insumo_id"]
                        ins_actual = supabase.table("insumos").select("stock_actual").eq("id", ins_id).single().execute().data
                        stock_previo = float(ins_actual.get("stock_actual", 0.0))
                        nuevo_stock = stock_previo + float(item["cant_base"])

                        supabase.table("insumos").update({
                            "stock_actual": nuevo_stock,
                            "costo_unidad": item["costo_unitario_base"]
                        }).eq("id", ins_id).execute()

                    st.success("🎉 ¡Compra registrada con éxito! Stock y costos unitarios actualizados.")
                    st.session_state.carrito_compra = []
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al procesar la factura: {e}")
