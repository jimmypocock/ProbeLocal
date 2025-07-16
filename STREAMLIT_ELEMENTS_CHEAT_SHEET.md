# Streamlit Elements Cheat Sheet

## Status/Alert Elements

- st.success() - Green success message
- st.info() - Blue info message
- st.warning() - Yellow warning message
- st.error() - Red error message
- st.exception() - Red exception with traceback

## Text Elements

- st.markdown() - Markdown text with formatting
- st.text() - Plain text
- st.caption() - Small gray text
- st.code() - Code block
- st.latex() - LaTeX equations
- st.divider() - Horizontal line

## Data Display

- st.metric() - Display metric with optional delta
- st.json() - Pretty JSON display
- st.dataframe() - Interactive dataframe
- st.table() - Static table

## Layout Elements

- st.container() - Group elements
- st.columns() - Multi-column layout
- st.expander() - Collapsible section
- st.tabs() - Tab interface
- st.sidebar - Sidebar content

## Interactive Elements

- st.button() - Clickable button
- st.toggle() - On/off switch
- st.selectbox() - Dropdown menu
- st.multiselect() - Multiple selection
- st.radio() - Radio buttons
- st.checkbox() - Single checkbox

## For your document status, you could use

- st.metric("Documents", len(docs), delta=None)
- st.info(f"📚 {len(docs)} documents...")
- st.markdown(f"**📚 {len(docs)} documents...**")
- st.caption(f"📚 {len(docs)} documents...")
