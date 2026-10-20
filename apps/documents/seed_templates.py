"""Textos legales por defecto (versión 1) de cada formulario.

Se usan como {placeholders} que se rellenan con los datos del caso al
generar/firmar. Los valores ya vienen escapados y con "—" donde aplica.
"""

DEFAULT_TEMPLATES = {
    "aob": {
        "title": "Cesión de beneficios (Assignment of Benefits)",
        "subtitle_tpl": "Caso: accidente del {accident_date} · Reclamo {claim_number}",
        "body_tpl": """
        <p>Yo, <strong>{patient_name}</strong> (fecha de nacimiento: {patient_dob}),
        por medio de la presente <strong>cedo, transfiero y asigno</strong> a
        <strong>{clinic_name}</strong> (NPI {clinic_npi}) todos mis derechos,
        títulos e intereses sobre los beneficios de Protección contra Lesiones Personales (PIP)
        pagaderos bajo mi póliza de seguro de auto Nº <strong>{policy_number}</strong>
        con <strong>{insurer}</strong>, en relación con las lesiones sufridas en el
        accidente ocurrido el <strong>{accident_date}</strong>.</p>
        <p>Esta cesión autoriza a la clínica a: presentar reclamos en mi nombre, recibir pagos
        directamente de la aseguradora, apelar denegaciones y, de ser necesario, ejercer las
        acciones legales correspondientes para el cobro de los servicios prestados.</p>
        <p>Entiendo que sigo siendo responsable de cualquier saldo no cubierto por mis beneficios
        PIP y que puedo revocar esta cesión por escrito en cualquier momento.</p>""",
        "signer_label": "Firma del paciente (o representante legal)",
        "legal_note": "Firma electrónica válida bajo ESIGN Act (15 U.S.C. ch. 96) y UETA de Florida (F.S. 668.50).",
    },
    "hipaa_auth": {
        "title": "Autorización para uso y divulgación de información de salud (HIPAA)",
        "subtitle_tpl": "Paciente: {patient_name} · Nacimiento: {patient_dob}",
        "body_tpl": """
        <p>Yo, <strong>{patient_name}</strong>, autorizo a <strong>{clinic_name}</strong>
        a usar y divulgar mi información protegida de salud (PHI) para los siguientes fines:</p>
        <ul>
          <li><strong>Tratamiento:</strong> coordinación de mi atención médica.</li>
          <li><strong>Pago:</strong> facturación y cobro a mi aseguradora ({insurer},
              póliza {policy_number}, reclamo {claim_number}).</li>
          <li><strong>Operaciones:</strong> administración de mi caso y cumplimiento legal.</li>
        </ul>
        <p>Esta autorización incluye notas clínicas, diagnósticos, estudios y facturación relacionados
        con el accidente del <strong>{accident_date}</strong>. Entiendo que:</p>
        <ul>
          <li>Puedo revocar esta autorización por escrito en cualquier momento.</li>
          <li>La revocación no afecta usos/divulgaciones ya realizados.</li>
          <li>El tratamiento no está condicionado a firmar esta autorización.</li>
          <li>Esta autorización vence 6 años después de mi última visita, o antes si la revoco.</li>
        </ul>""",
        "signer_label": "Firma del paciente (o representante legal)",
        "legal_note": "Conforme a 45 CFR 164.508. Firma electrónica válida bajo ESIGN/UETA.",
    },
    "tcpa_consent": {
        "title": "Consentimiento para mensajes de texto (TCPA)",
        "subtitle_tpl": "Paciente: {patient_name} · Teléfono: {patient_phone}",
        "body_tpl": """
        <p>Yo, <strong>{patient_name}</strong>, doy mi <strong>consentimiento expreso por
        escrito</strong> para que <strong>{clinic_name}</strong> me envíe mensajes de texto
        al número <strong>{patient_phone}</strong> con:</p>
        <ul>
          <li>Recordatorios de citas y confirmaciones.</li>
          <li>Avisos relacionados con mi tratamiento y mi caso.</li>
        </ul>
        <p><strong>Este consentimiento es SOLO para comunicaciones de salud. No acepto recibir
        mensajes de marketing.</strong> Entiendo que:</p>
        <ul>
          <li>Pueden aplicar tarifas de mensajes y datos de mi operador.</li>
          <li>Puedo revocar este consentimiento en cualquier momento respondiendo STOP o avisando
              en recepción; la clínica procesará la revocación dentro de 10 días hábiles.</li>
          <li>Dar mi número no es condición para recibir tratamiento.</li>
        </ul>""",
        "signer_label": "Firma del paciente",
        "legal_note": "Consentimiento expreso por escrito según TCPA (47 U.S.C. 227). Solo salud, no marketing.",
    },
    "consent_treat": {
        "title": "Consentimiento informado de tratamiento",
        "subtitle_tpl": "Paciente: {patient_name} · Caso: accidente del {accident_date}",
        "body_tpl": """
        <p>Yo, <strong>{patient_name}</strong>, autorizo a los profesionales de
        <strong>{clinic_name}</strong> a realizar la evaluación y el tratamiento que consideren
        necesario para mis lesiones del accidente del <strong>{accident_date}</strong>, incluyendo
        examen físico, ajustes quiroprácticos, terapia física y estudios diagnósticos.</p>
        <p>Entiendo que:</p>
        <ul>
          <li>Se me explicaron la naturaleza del tratamiento, sus beneficios y sus riesgos
              (incluyendo, aunque raros, empeoramiento temporal del dolor o lesión).</li>
          <li>Puedo hacer preguntas en cualquier momento y puedo retirar mi consentimiento.</li>
          <li>Ningún tratamiento garantiza un resultado específico.</li>
          <li>Mis registros podrán usarse para facturar a mi aseguradora según la cesión firmada.</li>
        </ul>""",
        "signer_label": "Firma del paciente (o representante legal)",
        "legal_note": "Consentimiento informado. Firma electrónica válida bajo ESIGN/UETA.",
    },
    "oir_b1_1571": {
        "title": "OIR-B1-1571 — Afirmación de servicios PIP",
        "subtitle_tpl": "Asegurado: {patient_name} · Póliza {policy_number} · Reclamo {claim_number}",
        "body_tpl": """
        <p>Yo, <strong>{patient_name}</strong>, asegurado bajo la póliza Nº
        <strong>{policy_number}</strong> de <strong>{insurer}</strong>,
        por medio de la presente <strong>afirmo</strong> que:</p>
        <ul>
          <li>Recibí tratamiento en <strong>{clinic_name}</strong> por las lesiones sufridas
              en el accidente del <strong>{accident_date}</strong>.</li>
          <li>Los servicios facturados me fueron explicados y efectivamente recibidos.</li>
          <li>La información que proporcioné para este reclamo es verdadera y correcta.</li>
        </ul>
        <p>Entiendo que cualquier declaración falsa puede constituir fraude de seguros bajo la ley
        de Florida (F.S. 817.234).</p>""",
        "signer_label": "Firma del asegurado (o tutor/representante)",
        "legal_note": "Formulario OIR-B1-1571. Firma electrónica válida bajo ESIGN/UETA.",
    },
    "gfe_ack": {
        "title": "Acuse de recibo — Estimado de buena fe (Good Faith Estimate)",
        "subtitle_tpl": "Paciente: {patient_name} (auto-pago / sin seguro)",
        "body_tpl": """
        <p>Yo, <strong>{patient_name}</strong>, acuso recibo del <strong>Estimado de Buena Fe</strong>
        entregado por <strong>{clinic_name}</strong> con el costo estimado de los servicios
        relacionados con el accidente del <strong>{accident_date}</strong>.</p>
        <p>Entiendo que:</p>
        <ul>
          <li>El estimado no es un contrato ni una factura final.</li>
          <li>Si la factura final excede el estimado en más de $400, tengo derecho a disputarla
              mediante el proceso de resolución paciente-proveedor (No Surprises Act).</li>
          <li>Puedo solicitar un estimado actualizado en cualquier momento.</li>
        </ul>""",
        "signer_label": "Firma del paciente",
        "legal_note": "No Surprises Act — 45 CFR 149.610. Firma electrónica válida bajo ESIGN/UETA.",
    },
    "disclosure_5e": {
        "title": "Declaración y reconocimiento — F.S. 627.736(5)(e)",
        "subtitle_tpl": "Paciente: {patient_name} · Accidente del {accident_date}",
        "body_tpl": """
        <div class="wetink-warning"><strong>ESTE DOCUMENTO REQUIERE FIRMA DE PUÑO Y LETRA.</strong>
        La ley exige la firma manuscrita del profesional y que el ORIGINAL se entregue a la
        aseguradora (no se acepta en formato electrónico).</div>
        <p>En relación con el tratamiento inicial del paciente <strong>{patient_name}</strong>
        por el accidente del <strong>{accident_date}</strong> (reclamo {claim_number},
        póliza {policy_number} de {insurer}), el profesional firmante declara
        bajo F.S. 627.736(5)(e):</p>
        <ul>
          <li>Que se informó al paciente sobre los beneficios PIP, sus derechos y las reglas de
              facturación aplicables.</li>
          <li>Que los servicios facturados son razonables, necesarios y están relacionados con el
              accidente.</li>
          <li>Que se lleva un registro cronológico de cada visita conforme a la ley.</li>
        </ul>
        <p><strong>Reconocimiento del paciente:</strong> declaro haber recibido esta información.</p>""",
        "signer_label": "Firma MANUSCRITA del profesional (puño y letra)",
        "legal_note": "F.S. 627.736(5)(e): firma manuscrita obligatoria; original a la aseguradora. NO firmar electrónicamente.",
    },
    "sworn_statement": {
        "title": "Declaración jurada — F.S. 627.736(6)(b)",
        "subtitle_tpl": "Declarante: {patient_name} · Reclamo {claim_number}",
        "body_tpl": """
        <div class="wetink-warning"><strong>DECLARACIÓN BAJO JURAMENTO.</strong>
        Debe firmarse de puño y letra, típicamente ante notario. Imprima este formulario precargado
        y complete la firma ante la autoridad correspondiente.</div>
        <p>Yo, <strong>{patient_name}</strong>, con fecha de nacimiento {patient_dob} y
        domicilio en {patient_address}, <strong>declaro bajo juramento</strong> en relación
        con el reclamo PIP Nº <strong>{claim_number}</strong> (póliza {policy_number},
        {insurer}) por el accidente del <strong>{accident_date}</strong>:</p>
        <ol>
          <li>Que la información proporcionada a <strong>{clinic_name}</strong> y a la aseguradora
              es verdadera y correcta.</li>
          <li>Que los tratamientos recibidos corresponden a las lesiones del accidente descrito.</li>
          <li>Que no he ocultado información relevante para la evaluación de este reclamo.</li>
        </ol>
        <p>Entiendo que una declaración falsa bajo juramento puede constituir fraude de seguros
        (F.S. 817.234) y perjurio.</p>
        <br><p>Jurado y suscrito ante mí el ____ de ____________ de 20____.</p>""",
        "signer_label": "Firma del declarante (puño y letra) + sello notarial",
        "legal_note": "F.S. 627.736(6)(b). Requiere juramento; firma manuscrita ante notario.",
    },
    "notice_initiation": {
        "title": "Aviso de inicio de tratamiento — F.S. 627.736(5)(c)",
        "subtitle_tpl": "De: {clinic_name} · Para: {insurer}",
        "body_tpl": """
        <p><strong>{clinic_name}</strong><br>{clinic_address}<br>
        Tel: {clinic_phone} · NPI: {clinic_npi}</p>
        <p>Fecha: _______________</p>
        <p>Para: <strong>{insurer}</strong> (aseguradora)<br>
        Re: Aviso de inicio de tratamiento — Reclamo PIP Nº <strong>{claim_number}</strong></p>
        <p>Por medio de la presente, <strong>{clinic_name}</strong> notifica el <strong>inicio de
        tratamiento</strong> del paciente <strong>{patient_name}</strong> (nacimiento:
        {patient_dob}) por las lesiones sufridas en el accidente del
        <strong>{accident_date}</strong>, bajo la póliza Nº <strong>{policy_number}</strong>.</p>
        <p>Este aviso se envía dentro de los 21 días del primer tratamiento conforme a
        F.S. 627.736(5)(c), extendiendo el plazo de presentación (timely filing) a 75 días.</p>""",
        "signer_label": "Firma del proveedor / director médico (puño y letra)",
        "legal_note": "Enviar a la aseguradora dentro de 21 días del inicio del tratamiento.",
    },
}
