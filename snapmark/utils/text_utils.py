def fix_mleader_styles(doc):
    """Corregge i MULTILEADER che puntano a stili inesistenti."""
    msp = doc.modelspace()
    valid_handles = {obj.dxf.handle for obj in doc.entitydb.values() 
                     if obj.dxftype() == 'MLEADERSTYLE'}
    
    for e in msp:
        if e.dxftype() == 'MULTILEADER':
            if e.dxf.style_handle not in valid_handles:
                # punta allo stile Standard
                standard = doc.mleader_styles.get('Standard')
                if standard:
                    e.dxf.style_handle = standard.dxf.handle