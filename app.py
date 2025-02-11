import streamlit as st
import pandas as pd
import json
import numpy as np
import altair as alt
import random
import math
import pdfkit  

#########################################################################
# (NYTT) PDF-FUNKTION FRAMFLYTTAD OCH UTÖKAD MED KOMMENTARER
#########################################################################
def generate_pdf_report(html_content: str) -> bytes:
    """
    Genererar en PDF från en HTML-sträng och returnerar PDF:en som bytes.
    Kräver att pdfkit och wkhtmltopdf är installerade och i PATH.
    
    Du kan behöva ange en config:
      config = pdfkit.configuration(wkhtmltopdf="/usr/local/bin/wkhtmltopdf")
    Och sedan anropa:
      pdf_bytes = pdfkit.from_string(html_content, False, configuration=config)
    Nedan kör vi utan explicit config.
    """
    try:
        config = pdfkit.configuration(wkhtmltopdf="/usr/local/bin/wkhtmltopdf")
        pdf_bytes = pdfkit.from_string(html_content, False, configuration=config)
        return pdf_bytes
    except Exception as e:
        print("Fel vid generering av PDF:", e)
        return b""

#########################################################################
# 1) Färgkodning av rader i tabell
#########################################################################
def color_row_style(row):
    """
    Villkorsstyrd färg på rad i tabellen baserat på 'Ny post. %'.
    Här markerar vi t.ex. 
       >95% = röd bakgrund (bortom rimligt tvivel),
       >80% = orange bakgrund (starkt för skuld).
    """
    new_post_str = row.get("Ny post. %", "")
    try:
        new_post_val = float(new_post_str.replace(",", "."))
    except:
        new_post_val = 0.0

    if new_post_val >= 95.0:
        return ["background-color: #FFCCCC"] * len(row)
    elif new_post_val >= 80.0:
        return ["background-color: #FFE5CC"] * len(row)
    else:
        return [""] * len(row)

#########################################################################
# 2) Hjälpfunktion format_auto_decimals
#########################################################################
def format_auto_decimals(x: float, max_decimals: int = 10) -> str:
    """
    Formaterar talet x med upp till max_decimals decimaler,
    men döljer onödiga nollor så man inte alltid ser "0.0000000000".
    Exempel:
      0.012300 -> "0.0123"
      123.0    -> "123"
    """
    s = f"{x:.{max_decimals}f}"
    s = s.rstrip('0').rstrip('.')
    if s == "" or s == "-":
        s = "0"
    return s

#########################################################################
# 3) Tolkning i ord 
#########################################################################
def interpret_probability_in_words(pct: float) -> str:
    """
    Returnerar en enkel textbedömning baserat på pct (0..100).
    Ex: bortom rimligt tvivel ~95%?
    Justera gränserna som du vill.
    """
    if pct >= 95:
        return "Ställt butom rimligt"
    elif pct >= 80:
        return "Klart övervägande skäl"
    elif pct >= 60:
        return "I huvudsak styrkt"
    elif pct >= 50:
        return "Cirka hälften / liten övervikt"
    elif pct >= 40:
        return "Tveksamt"
    elif pct >= 20:
        return "Osannolikt"
    elif pct >= 1:
        return "Praktiskt taget ingen chans"
    else:
        return "Mycket nära omöjligt"

#########################################################################
# 4) Huvudfunktion
#########################################################################
def main():
    st.set_page_config(page_title="Bevisvärdering (Bayes)", layout="wide")

    st.title("Lambertz kalkylator för bevisvärdering")
    st.markdown("""
    **Välkommen!**  
    Denna applikation demonstrerar hur man kan värdera bevisning i juridiska fall med olika metoder:
    - **Enkel Bayes** (stegvis)
    - **Bayesian Network** (stjärnstruktur)
    - **Dempster–Shafer**
    """)

    # EXTRA TILLÄGG (förslag 5) – Introduktion / referenser till Lambertz PM
    with st.expander("Om Bayes i juridik (Lambertz PM)"):
        st.markdown("""
        I en juridisk kontext (enligt **Lambertz PM** s. 45–47) betonas att:
        
        - Tillämpningen av Bayes i brottmål handlar inte bara om att göra en matematisk uträkning.
        - Man måste även ta hänsyn till huruvida bevisen är oberoende, om bevis finns som talar emot skuld,
          och om det finns standardvärden (ex. "DNA ≈ 95%").
        - Bevisvärdering kräver en allsidig bedömning, men en Bayes-ansats kan vara ett pedagogiskt verktyg
          för att tydliggöra hur nya bevis påverkar sannolikheten.
        
        **Lambertz PM** pekar på vikten av att inte bara lita på resultatet av denna kalkylator,
        utan också förstå att t.ex. vittnesbevis kan vara feltolkat, att bevis ibland är beroende av varandra,
        och att kritiska sannolikhetsgränser (som 95% eller 80%) är vägledande snarare än absoluta.
        
        _Läs mer i Lambertz PM s. 45–47 för fördjupad diskussion om bevisvärdering och statistiska metoder._
        """)

    # Extra förklaring
    with st.expander("Steg-för-steg-guide"):
        st.markdown("""
        **Steg 1**: Ange din *ursprungliga sannolikhet* (prior).  
        **Steg 2**: Välj hur många bevis du vill mata in.  
        **Steg 3**: Ange för varje bevis sannolikheten om personen är skyldig vs. oskyldig.  
        **Steg 4**: Klicka 'Beräkna' för att få slutlig sannolikhet och en tolkning i ord.  
        Om du väljer 'Intervall–Bayes' kan du sätta min–max i stället för exakta siffror.

        *(Denna beräkning är inspirerad av Probability-läget i 'X vs Y' i USA, se dok. 2022:45)*
        """)

    # Förklaring procentsatser
    with st.expander("Förklaring av kritiska procentsatser"):
       st.write("""
     **Procentsatser är ovanliga i domar**  
     - Domstolar anger sällan eller aldrig procentsiffror för sannolikhet.  
     - Procentsatser används oftare pedagogiskt i juridisk litteratur och undervisning för att förklara beviskravsnivåer.  
     - I svensk rättspraxis hittar man snarare fraser som ”styrkt”, ”visat”, ”anförda omständigheter talar för” och ”utom rimligt tvivel”.  
     - För denna kalkylator måste dock bevisvärderingen omvandlas till procentsatser.  

     Nedan ges exempel på sådana (ej officiella, utan teoretiska riktlinjer):
     - **20 %**: Osannolikt  
     - **40 %**: Tveksamt  
     - **50 %**: Cirka hälften (50/50-läge)  
     - **60 %**: I huvudsak styrkt  
     - **80 %**: Klart övervägande skäl  
     - **100 %**: Ställt utom rimligt tvivel  

     Vanliga begrepp som har relevans för bevisvärdering är främst de som är lagfästa eller vedertagna, såsom ”skälig misstanke”, ”på sannolika skäl misstänkt”, ”bevisövervikt” och ”ställt utom rimligt tvivel”. Formuleringar som ”osannolikt” eller ”tveksamt” förekommer också men då som en fri bedömning i domskälen, inte som formella ”nivåer”. Procentsatser (t.ex. 20 %, 50 %, 80 %) är inte något man brukar se i själva domarna. De är mest ett teoretiskt hjälpmedel för att illustrera skillnader i beviskrav.

     ---

     I svensk juridisk praktik och i domar förekommer vissa återkommande uttryck för olika beviskrav och misstankegrader. Nedan följer en översikt av några sådana termer som faktiskt återfinns i förarbeten, lagtext (framför allt i rättegångsbalken) och inte minst i domar eller beslut från domstolar:

     ### 1. Misstankegrader i brottmål

     1. **Skälig misstanke (Ca 20–30 %)**
        - Lagstadgad term (t.ex. 24 kap. 1 § rättegångsbalken).
        - Används bl.a. vid beslut om tvångsmedel (gripande, anhållande).
        - I domstolars häktningsbeslut kan man se formuleringar som ”Det föreligger skälig misstanke mot NN…”.

     2. **På sannolika skäl misstänkt (Ca 40–50 %)**
        - Nästa misstankegrad (t.ex. 24 kap. 2 § rättegångsbalken).
        - Ofta formulerat i domstolsbeslut eller protokoll som ”åklagaren har visat att det finns sannolika skäl för att NN har begått gärningen”.

     3. **Tillräckliga skäl för åtal (Ca 60–70 %)**
        - Inget procenttal nämns i lagtexten, men åklagaren ska anse sig kunna förvänta en fällande dom för att väcka åtal.
        - I praktiken är detta ett ännu högre krav än ”sannolika skäl”.

     4. **Ställt utom rimligt tvivel (Ca 90–95 %, vissa säger 95–99 %)**
        - Det högsta beviskravet i brottmål.
        - I domar från både tingsrätt, hovrätt och Högsta domstolen (HD) kan man se skrivningar som ”Åklagaren har visat bortom rimligt tvivel att NN gjort sig skyldig till…”.
        - Även formuleringen ”utom allt rimligt tvivel” förekommer.

     ---  

     ### 2. Beviskrav i civilmål

     1. **Bevisövervikt (Strax över 50 %, t.ex. 51–60 %)**
        - Det vanligaste beviskravet i civilrätten (t.ex. i tvistemål).
        - Domar innehåller ofta formuleringar som ”Käranden har bevisbördan för att fordran existerar och denna bevisbörda har uppfyllts genom …”, eller ”Domstolen bedömer att [parten] visat sin talan med tillräcklig styrka (bevisövervikt).”

     2. **Styrkt / inte styrkt**
        - Mycket vanligt i domslut och domskäl: ”Domstolen finner därmed visat…” eller ”Det är inte styrkt att…”.
        - Här används ofta fraser som ”utredningen talar för att…” eller ”det får anses utrett…” för att markera att ett påstående anses bevisat.
        - Styrkt: > 50–60 % (uppfyller det aktuella kravet, oftast ”bevisövervikt”)
        - Inte styrkt: < 50 % (uppfyller inte kravet, alltså under ”bevisövervikt”).

     3. **”Högre” beviskrav i vissa undantagsfall**
        - I vissa speciallagar eller särskilda situationer (t.ex. i tryckfrihetsmål eller mål rörande tvångsvård) kan det närma sig ett slags ”klart och övertygande” krav. Det är dock mest en terminologi känd från angloamerikansk rätt (”clear and convincing evidence”).
        - I svensk praxis benämns det inte alltid lika formellt, men man kan se formuleringar som ”mycket stark bevisning krävs” i vissa rättsfall.

     ---

     ### 3. Termer som ibland dyker upp i domskäl

     - **”Osannolikt” / ”föga sannolikt” (Under ca 20–30 %)**  
       Dessa ord kan förekomma i domskäl när domstolen värderar en parts påstående, t.ex. ”Domstolen anser att det är föga sannolikt att NN …”. De används dock mer sällan som en formell ”nivå” utan snarare som en värdering av bevisningen.

     - **”Tveksamt” / ”osäkert” (Kring 30–50 %)**  
       Används i domar när bevisningen inte räcker: ”Det finns tveksamheter kring…” eller ”Domstolen finner det osäkert…”. Leder ofta till slutsatsen att det inte är styrkt.

     - **”Klart övervägande skäl” (Ca 70–80 %)**  
       Inte en fast juridisk term i svensk lagstiftning, men uttrycket kan förekomma i domskäl eller i juristers argumentation, exempelvis i förvaltningsmål, för att markera att de skäl som talar för en viss bedömning är avsevärt starkare. Är alltså mer ett vanligt språkbruk än en precis bevisteknisk term.
     """)

    # Antaganden & begränsningar
    with st.expander("Antaganden & begränsningar"):
        st.markdown("""
        **1. Oberoende bevis**  
        Vi förutsätter i grundmodellen att bevisen är oberoende av varandra (givet skuld eller oskuld). 
        Om bevisen i verkligheten korrelerar kan modellen överskatta sannolikheten.
        Om man klickar in 7–8 bevis med höga ”P(B|A) / P(B|¬A)”-kvoter kan posteriorsannolikheten bli fullständigt skenande, trots att bevisen i praktiken inte är genuint oberoende. Detta är en typisk naiv-Bayes-brist.
        
        I Lambertz PM (och i allmän juridisk diskussion) poängteras att många bevis inte är oberoende av varandra. I den här kalkylatorn utgår vi däremot från att varje nytt bevis kan matas in separat (eller i en stjärnstruktur) utan att ta hänsyn till korrelationer. Detta är en vanlig, men potentiellt stor, förenkling. Om två bevis i verkligheten korrelerar (t.ex. två vittnesmål som påverkar varandra) kommer kalkylatorn riskera att överskatta eller underskatta den samlade styrkan.

        **2. Subjektiv bedömning**  
        Sannolikheten för att ett visst bevis uppstår (P(B|A) eller P(B|¬A)) är ofta en subjektiv uppskattning. 
        Man kan använda expertbedömningar eller typiska standardvärden (t.ex. "DNA: 95%"). Det kan hjälpa att resonera lite extra eller ta hjälp av AI (ChatGPT).

        **3. Felkällor & risker**  
        - Om bevisen inte är oberoende riskerar modellen att multiplicera sannolikhet i onödan.  
        - Vissa bevis kan ha dubbelräknats.  
        - Den ursprungliga prioren (P(A)) kan också vara svår att fastställa.  
        - Ny information kan förändra bedömningarna i grunden.
        - Det finns en risk för kumulativa avrundningar.
          Kalkylatorn beräknar exakt i varje steg, vilket i normalfallet är bra. Men Lambertz och andra jurister kan ibland göra avrundningar mellan varje bevismoment. Det kan leda till en något annan slutpost (lite större avvikelse) än en exakt beräkning i en dator.

        **4. Hantering av ”motbevis” är enkel, men kräver manuell tolkning**  
        Denna app illustrerar en Bayes-modell. I verkliga rättsfall måste domstolen göra en mer heltäckande bevisvärdering, inte enbart förlita sig på en matematisk modell. I Lambertz promemorior vävs ofta motbevis in genom att man för vissa bevis sätter P(B∣A) lägre och P(B∣¬A) högre. I den här kkalkylatorn har vi lagt en egen sektion ”negative evidence” där man på nytt kör samma Bayes-formel, men tolkar motbeviset MB som ”starkare sannolikt om oskyldig än om skyldig”. Det kan fungera om man verkligen definierar motbeviset MB (”Den åtalade har alibi”, ”Hunden markerade inte alls”, etc.) med sina sannolikheter, men det förutsätter att man själv sätter siffrorna på rätt sätt och att beviset är (återigen) ”oberoende”. Det kan hjälpa att resonera själv eller tillsammans med AI (ChatGPT). Gör man felbedömningar här kan man få förvirrande resultat. Notera också att koden adderar motbevis i efterhand (post-hoc) i samma kedja, vilket i och för sig är en legitim användning av Bayes formel, men det blir lättare att göra misstag om man inte noga definierar P(MB∣A) kontra P(MB∣¬A).
        
        **5. Användning i juridik**  
        Denna app illustrerar en Bayes-modell. I verkliga rättsfall måste domstolen göra en mer heltäckande 
        bevisvärdering, inte enbart förlita sig på en matematisk modell.
        
        *(Dessa begränsningar bör du alltid beakta när du presenterar resultatet för en domstol eller klient.)*
        """)

    metod = st.selectbox(
        "Välj metod:",
        ["Välj...", "1. Enkel Bayes (stegvis)", "2. Bayesian Network (stjärna)", "3. Dempster–Shafer (grund)"]
    )

    if metod == "1. Enkel Bayes (stegvis)":
        enkel_bayes()
    elif metod == "2. Bayesian Network (stjärna)":
        bayesian_network_demo()
    elif metod == "3. Dempster–Shafer (grund)":
        dempster_shafer_demo()
    else:
        st.write("Välj en metod i listan ovan.")

#########################################################################
# 5) ENKEL BAYES (med scenariolagring, bevismallar mm)
#########################################################################
def enkel_bayes():
    st.header("Enkel Bayes – Stegvis uppdatering")
    st.markdown(r"""
    I **Enkel Bayes** uppdaterar du sannolikheten för skuld bevis för bevis:
                
    P (A givet B) = [P (B givet A) x P (A)] / [P (B givet A) x P (A)] + [P (B givet ej A) x P (ej A)].
                
    I ord kan satsen beskrivas enligt följande:
    Sannolikheten för skuld givet en viss omständighet är lika med [sannolikheten för att omständigheten föreligger givet skuld gånger ”ursprungssannolikheten” för skuld] delat med [sannolikheten för att omständigheten föreligger givet skuld gånger ”ursprungssanno-likheten” för skuld] plus [sannolikheten för att omständigheten fö-religger givet oskuld gånger ursprungssannolikheten för oskuld].
    När man använder denna formel för att beräkna det ackumule-rade värdet av flera bevis får man räkna med ett bevis i taget. När man har gjort beräkningen för ett bevis går man vidare till nästa, varvid resultatet av den föregående beräkningen inkorporeras i A på så sätt att ursprungssannolikheten, P (A), i den följande beräk-ningen tar hänsyn till det bevis som användes i den föregående. I det första steget står alltså A för ”skuld utan bevis”, i det andra steget för ”skuld när hänsyn tas till det bevis som användes vid den förra beräkningen” osv.

    - Ange *ursprunglig sannolikhet* (prior).
    - Ange *P(B|A)* och *P(B|¬A)* för varje bevis.
    - Klicka *Beräkna Bayes (Exakt)* eller använd *Monte Carlo*-simulering i intervall-läget.
    
    Utöver detta finns hantering av ”motbevis” (där koden återigen kör Bayes formel men tolkar motbeviset som en ny observation "MB" vars sannolikhet är större om den misstänkte är oskyldig
    """)

    # Prompt-text som ska användas om man vill ha ChatGPTs hjälp
    HELP_PROMPT_TEXT = """
Jag vill göra en Bayes- bedömning av ett bevis i ett hypotetiskt rättsfall. 
Beviset är: [Beskriv beviset kort, t.ex. "Ett vittnesmål från en granne som såg en person lämna brottsplatsen."]

**Min fråga handlar om att uppskatta två sannolikheter:**
1. P(B|A) – Sannolikhet att detta bevis uppstår om den misstänkte är skyldig.
2. P(B|¬A) – Sannolikhet att detta bevis uppstår om den misstänkte i stället är oskyldig.

Jag vill att du, ChatGPT, systematiskt hjälper mig att:
- Redogöra för vilka faktorer jag bör väga in när jag bedömer dessa två sannolikheter.
- Ge konkreta exempel på omständigheter som höjer respektive sänker P(B|A).
- Ge konkreta exempel på omständigheter som höjer respektive sänker P(B|¬A).
- Försiktigt föreslå ett möjligt intervall (t.ex. 40–60 % eller 0,1–1 %) för vardera av dessa sannolikheter, 
  med en kort motivering baserad på de listade faktorerna.
- Redovisa eventuella felkällor och brister i bedömningen (t.ex. osäkerhet i vittnets minne, möjlig förväxling, 
  om det finns incitament att ljuga etc.).
- Förtydliga att detta är en subjektiv uppskattning och att mer information kan ändra slutsatsen.

**Format på svaret**:
1. **Faktorer att väga in**:
   - ...
   - ...

2. **Omständigheter som påverkar P(B|A)**:
   - ...
   - ...

3. **Omständigheter som påverkar P(B|¬A)**:
   - ...
   - ...

4. **Möjligt intervall för P(B|A) och P(B|¬A)**:
   - ... (med kort motivering)

5. **Eventuella felkällor och begränsningar**:

Poängtera gärna också om det finns någon relevant praxis eller standardvärden i juridiskt sammanhang.

Om något är oklart, fråga mig. Annars – ge ett sammanhållet svar som är anpassat för en jurist som vill förstå 
bevisets styrka i en Bayes-kedja.

**Klistra in denna prompt i ChatGPT och ersätt [Beskriv beviset kort...] med ditt eget bevis.**
"""

    st.sidebar.markdown("**Motbevis (frivilligt)**")
    enable_negative_evidence = st.sidebar.checkbox(
        "Aktivera 'motbevis'-sektion", 
        help="Kryssa i om du vill lägga till separata bevis som explicit talar emot skuld."
    )

    negative_bevis_data = []
    negative_count = 0
    if enable_negative_evidence:
        negative_count = st.sidebar.number_input(
            "Antal motbevis",
            help="Hur många explicita motbevis du vill mata in.",
            min_value=1,
            max_value=20,
            value=1,
            step=1
        )

    def prior_callback():
        st.session_state["bayes_prior_val"] = st.session_state["widget_prior"]
    if "bayes_prior_val" not in st.session_state:
        st.session_state["bayes_prior_val"] = 0.01

    prior_percent = st.sidebar.number_input(
        "Ursprunglig sannolikhet (%)",
        help="Ex: 0.01 motsvarar 0.01%.",
        min_value=0.0,
        max_value=100.0,
        value=st.session_state["bayes_prior_val"],
        step=1e-7,
        format="%.9g",
        key="widget_prior",
        on_change=prior_callback
    )
    prior = prior_percent / 100.0

    def antal_callback():
        st.session_state["bayes_antal_val"] = st.session_state["widget_antal"]
    if "bayes_antal_val" not in st.session_state:
        st.session_state["bayes_antal_val"] = 3
    antal = st.sidebar.number_input(
        "Antal bevis",
        min_value=1,
        max_value=20,
        value=st.session_state["bayes_antal_val"],
        step=1,
        key="widget_antal",
        on_change=antal_callback
    )

    if "widget_use_intervals" not in st.session_state:
        st.session_state["widget_use_intervals"] = False
    use_intervals = st.sidebar.checkbox(
        "Intervall–Bayes (min–max)",
        help="Om kryssad: bevisen anges som min–max i %, annars en exakt siffra.",
        value=st.session_state["widget_use_intervals"],
        key="widget_use_intervals"
    )

    st.write(f"**Aktuell prior**: {format_auto_decimals(prior*100)} %")
    st.write(f"**Antal bevis**: {antal}")
    st.write(f"**Intervall-läge**: {use_intervals}")

    with st.expander("Exempel på typiska sannolikheter (mall)"):
        st.markdown("""
        - **Fingeravtryck**: P(B|A) ~80 %, P(B|¬A) ~5 %  
        - **DNA-träff**: P(B|A) ~95 %, P(B|¬A) ~0.1 %  
        - **Vittnesmål** (pålitlig): P(B|A) ~60 %, P(B|¬A) ~20 %  
        - **Vittnesmål** (osäker): P(B|A) ~55 %, P(B|¬A) ~35 %  
        """)

    tabs = st.tabs([f"Bevis {i+1}" for i in range(antal)])
    bevis_data = []
    for i in range(antal):
        with tabs[i]:
            desc_key = f"desc_{i}"
            if desc_key not in st.session_state:
                st.session_state[desc_key] = f"Bevis {i+1}"
            st.text_input(f"Beskriv bevis {i+1}:", key=desc_key)

            if st.button(f"Hjälp mig att värdera beviset", key=f"help_prompt_{i}"):
                st.info(
                    "Nedan är en prompt du kan kopiera och klistra in i ChatGPT:\n\n"
                    f"```\n{HELP_PROMPT_TEXT}\n```\n"
                    "Ersätt texten [Beskriv beviset kort...] med:\n"
                    f"'{st.session_state[desc_key]}'\n"
                    "På så vis får du förslag på hur du kan resonera kring just detta bevis."
                )

            if use_intervals:
                pbga_min_key = f"pbga_{i}_min"
                pbga_max_key = f"pbga_{i}_max"
                if pbga_min_key not in st.session_state:
                    st.session_state[pbga_min_key] = 50.0
                if pbga_max_key not in st.session_state:
                    st.session_state[pbga_max_key] = 60.0

                val_min_a = st.number_input(
                    "P(B|A) min (%)",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[pbga_min_key],
                    step=1e-7, format="%.9g", key=pbga_min_key
                )
                val_max_a = st.number_input(
                    "P(B|A) max (%)",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[pbga_max_key],
                    step=1e-7, format="%.9g", key=pbga_max_key
                )

                pbgna_min_key = f"pbgna_{i}_min"
                pbgna_max_key = f"pbgna_{i}_max"
                if pbgna_min_key not in st.session_state:
                    st.session_state[pbgna_min_key] = 5.0
                if pbgna_max_key not in st.session_state:
                    st.session_state[pbgna_max_key] = 10.0

                val_min_na = st.number_input(
                    "P(B|¬A) min (%)",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[pbgna_min_key],
                    step=1e-7, format="%.9g", key=pbgna_min_key
                )
                val_max_na = st.number_input(
                    "P(B|¬A) max (%)",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[pbgna_max_key],
                    step=1e-7, format="%.9g", key=pbgna_max_key
                )

                bevis_data.append(
                    (val_min_a/100.0, val_max_a/100.0, val_min_na/100.0, val_max_na/100.0)
                )
            else:
                pbga_key = f"pbga_{i}"
                if pbga_key not in st.session_state:
                    st.session_state[pbga_key] = 50.0
                p_b_given_a_val = st.number_input(
                    "P(B|A) i %",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[pbga_key],
                    step=1e-7, format="%.9g", key=pbga_key
                )

                pbgna_key = f"pbgna_{i}"
                if pbgna_key not in st.session_state:
                    st.session_state[pbgna_key] = 10.0
                p_b_given_not_a_val = st.number_input(
                    "P(B|¬A) i %",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[pbgna_key],
                    step=1e-7, format="%.9g", key=pbgna_key
                )
                bevis_data.append(
                    (p_b_given_a_val/100.0, p_b_given_not_a_val/100.0)
                )

    if enable_negative_evidence and negative_count > 0:
        negative_tabs = st.tabs([f"Motbevis {i+1}" for i in range(negative_count)])
        negative_bevis_data.clear()
        for i in range(negative_count):
            with negative_tabs[i]:
                st.markdown("Här anger du ett bevis som talar MOT skuld (fäller sannolikheten).")
                desc_neg_key = f"desc_neg_{i}"
                if desc_neg_key not in st.session_state:
                    st.session_state[desc_neg_key] = f"Motbevis {i+1}"
                st.text_input(f"Beskriv motbevis {i+1}:", key=desc_neg_key)

                nbga_key = f"nbga_{i}"
                if nbga_key not in st.session_state:
                    st.session_state[nbga_key] = 30.0
                nbga_val = st.number_input(
                    "P(Motbevis|Skuld) i %",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[nbga_key],
                    step=1e-7, format="%.9g", key=nbga_key
                )

                nbgna_key = f"nbgna_{i}"
                if nbgna_key not in st.session_state:
                    st.session_state[nbgna_key] = 70.0
                nbgna_val = st.number_input(
                    "P(Motbevis|Oskuld) i %",
                    min_value=0.0, max_value=100.0,
                    value=st.session_state[nbgna_key],
                    step=1e-7, format="%.9g", key=nbgna_key
                )

                negative_bevis_data.append( (nbga_val/100.0, nbgna_val/100.0) )

    st.markdown("### Sammanfattning av inmatade bevis (innan beräkning)")
    if use_intervals:
        summ_rows = []
        for i, (amina, amax, nmina, nmax) in enumerate(bevis_data, start=1):
            summ_rows.append({
                "Bevis #": i,
                "P(B|A) min–max": f"{format_auto_decimals(amina*100)}–{format_auto_decimals(amax*100)}",
                "P(B|¬A) min–max": f"{format_auto_decimals(nmina*100)}–{format_auto_decimals(nmax*100)}"
            })
        st.table(summ_rows)
    else:
        summ_rows = []
        for i, (pba, pbna) in enumerate(bevis_data, start=1):
            summ_rows.append({
                "Bevis #": i,
                "P(B|A)": format_auto_decimals(pba*100),
                "P(B|¬A)": format_auto_decimals(pbna*100),
            })
        st.table(summ_rows)

    if enable_negative_evidence and negative_count > 0:
        st.markdown("### Motbevis (talar emot skuld)")
        st.write("Dessa bevis förväntas höja sannolikheten om *oskuld* mer än om *skuld*.")
        for i, (nbga, nbgna) in enumerate(negative_bevis_data, start=1):
            st.write(
                f"- Motbevis {i}: P(MB|Skuld)={format_auto_decimals(nbga*100)}%, "
                f"P(MB|Oskuld)={format_auto_decimals(nbgna*100)}%. "
                "(Större värde i P(MB|Oskuld) => sänker samlad sannolikhet för skuld.)"
            )

    colA, colB = st.columns(2)
    from math import floor, ceil

    # Hållare för vår slutliga sannolikhet i session state
    # (så vi kan visa PDF-knapp även efter omkörning)
    if "final_in_pct" not in st.session_state:
        st.session_state["final_in_pct"] = None

    with colA:
        if st.button("Beräkna Bayes (Exakt)"):
            result = do_exact_bayes_calculation(prior, bevis_data, use_intervals)
            if enable_negative_evidence and negative_count > 0:
                if use_intervals:
                    # Existerande varning (vi ska inte ta bort den)
                    st.warning("Motbevis + intervall-läge ej fullständigt implementerat i denna demo.")
                    #########################################################################
                    # (PATCH for motbevis + intervals)
                    # Nedan kod lägger in motbevis i min/median/max
                    #########################################################################
                    min_post_list, median_post_list, max_post_list = result
                    current_min = min_post_list[-1]
                    current_median = median_post_list[-1]
                    current_max = max_post_list[-1]

                    # Vi gör en enkel loop som uppdaterar min, median, max för varje motbevis
                    for (nbga, nbgna) in negative_bevis_data:
                        # min
                        num_min = nbga * current_min
                        den_min = num_min + nbgna*(1 - current_min)
                        new_min = num_min/den_min if den_min != 0 else 0
                        current_min = new_min

                        # median
                        num_med = nbga * current_median
                        den_med = num_med + nbgna*(1 - current_median)
                        new_med = num_med/den_med if den_med != 0 else 0
                        current_median = new_med

                        # max
                        num_max = nbga * current_max
                        den_max = num_max + nbgna*(1 - current_max)
                        new_max = num_max/den_max if den_max != 0 else 0
                        current_max = new_max

                    min_post_list.append(current_min)
                    median_post_list.append(current_median)
                    max_post_list.append(current_max)

                    st.markdown("#### Slutlig sannolikhet (inkl. motbevis) – Intervall:")
                    st.write(f"- **Min (%)**: {format_auto_decimals(current_min*100)}")
                    st.write(f"- **Median (%)**: {format_auto_decimals(current_median*100)}")
                    st.write(f"- **Max (%)**: {format_auto_decimals(current_max*100)}")

                    # Sätt final_in_pct till median
                    st.session_state["final_in_pct"] = current_median*100

                    # (NY KOD: Visa även en tabell över alla steg i min/median/max, nu när motbevis är klara)
                    st.markdown("### Resultat för Intervall-Bayes (inkl. motbevis)")
                    intervals_data_motbevis = []
                    for step_idx, (pmin, pmed, pmax) in enumerate(zip(min_post_list, median_post_list, max_post_list)):
                        intervals_data_motbevis.append({
                            "Steg": step_idx,
                            "Min (%)": f"{pmin*100:.2f}",
                            "Median (%)": f"{pmed*100:.2f}",
                            "Max (%)": f"{pmax*100:.2f}",
                        })
                    df_intervals_motbevis = pd.DataFrame(intervals_data_motbevis)
                    st.dataframe(df_intervals_motbevis)

                else:
                    posterior_list, row_list = result
                    current_post = posterior_list[-1]
                    row_list_final = row_list
                    i_beviscount = len(row_list)

                    for (nbga, nbgna) in negative_bevis_data:
                        i_beviscount += 1
                        old = current_post
                        numerator = nbga * old
                        denominator = numerator + nbgna*(1 - old)
                        new_p = numerator/denominator if denominator!=0 else 0
                        delta = (new_p - old)*100
                        new_p_pct = new_p*100

                        if new_p_pct >= 95:
                            komm = "Bortom rimligt tvivel (>95%)"
                        elif new_p_pct >= 80:
                            komm = "Starkt för skuld (>80%)"
                        elif new_p_pct >= 50:
                            komm = "Delvis för skuld (>50%)"
                        else:
                            komm = "Under 50%"

                        row_list_final.append({
                            "Bevis #": f"Motbevis {i_beviscount}",
                            "P(B|A)": format_auto_decimals(nbga*100),
                            "P(B|¬A)": format_auto_decimals(nbgna*100),
                            "Gammal post. %": format_auto_decimals(old*100),
                            "Ny post. %": format_auto_decimals(new_p_pct),
                            "Förändring (pp)": format_auto_decimals(delta),
                            "Kommentar": komm
                        })
                        current_post = new_p
                        posterior_list.append(new_p)

                    df_style2 = pd.DataFrame(row_list_final).style.apply(color_row_style, axis=1)
                    st.write(df_style2.to_html(escape=False), unsafe_allow_html=True)
                    final_post = posterior_list[-1]*100
                    st.success(f"Slutlig sannolikhet (inkl. motbevis) = {format_auto_decimals(final_post)} %")

                    # Spara i sessionen
                    st.session_state["final_in_pct"] = final_post
                    return
            if use_intervals:
                # Om man inte har motbevis, eller om negative_count=0
                if enable_negative_evidence and negative_count>0:
                    # Redan hanterat i patch
                    pass
                else:
                    min_post_list, median_post_list, max_post_list = result
                    st.markdown("### Resultat för Intervall-Bayes")
                    intervals_data = []
                    for i, (pmin, pmed, pmax) in enumerate(zip(min_post_list, median_post_list, max_post_list)):
                        intervals_data.append({
                            "Steg": i,
                            "Min (%)": f"{pmin*100:.2f}",
                            "Median (%)": f"{pmed*100:.2f}",
                            "Max (%)": f"{pmax*100:.2f}",
                        })

                    df_intervals = pd.DataFrame(intervals_data)
                    st.dataframe(df_intervals)
                    st.info("Motbevis inaktiverat eller inga motbevis angivna.")
                     # (NY KOD: Villkor för motbevis-meddelande)
                    if not (enable_negative_evidence and negative_count>0):
                        st.info("Motbevis inaktiverat eller inga motbevis angivna.")
           
            else:
                posterior_list, row_list = result
                df_style = pd.DataFrame(row_list).style.apply(color_row_style, axis=1)
                st.write(df_style.to_html(escape=False), unsafe_allow_html=True)
                final_in_pct = posterior_list[-1]*100
                st.success(f"Slutlig sannolikhet för skuld: {format_auto_decimals(final_in_pct)} %")
                st.info("Motbevis inaktiverat eller inga motbevis angivna.")

                # (NY KOD: Villkor för motbevis-meddelande)
                if not (enable_negative_evidence and negative_count>0):
                    st.info("Motbevis inaktiverat eller inga motbevis angivna.")

                # Spara i sessionen
                st.session_state["final_in_pct"] = final_in_pct

                #########################################################################
                # (NYTT) EXEMPEL PÅ TILLÄGG – VISA HELA EKVATIONEN OCH FÖRKLARANDE TEXT
                #########################################################################
                st.markdown("### Visad ekvation (kontroll)")
                st.markdown(r"""
                **Här är ekvationen som används för varje nytt bevis i enkel Bayes:**

                \[
                P(\skyldig \mid \Bevis1) \;=\; \frac{\,P(\Bevis1 \mid \skyldig)\;P(\skyldig)\,}{\,P(\Bevis1 \mid \skyldig)\;P(\skyldig)\;+\;P(\Bevis1 \mid \oskyldig)\,\bigl(1 - P(\skyldig)\bigr).
                \]

                - Här symboliserar \(\text{skyldig}\) händelsen att personen faktiskt är skyldig (A).
                - \(\text{Bevis1}\) symboliserar att beviset finns eller att vi observerat det.
                - \(\text{oskyldig}\) är motsatsen, dvs. att personen inte är skyldig (\(\neg A\)).

                Denna formel motsvarar Bayes sats anpassad för "skuld" vs "oskuld", där:
                - \(P(\text{skyldig})\) är den gamla posten (priorn).
                - \(P(\text{Bevis1} \mid \text{skyldig})\) är sannolikheten att Bevis1 uppträder om personen är skyldig.
                - \(P(\text{Bevis1} \mid \text{oskyldig})\) är sannolikheten att Bevis1 uppträder om personen är oskyldig.
                - \(\bigl(1 - P(\text{skyldig})\bigr)\) är sannolikheten för att personen är oskyldig.

                Varje nytt bevis beräknas på detta sätt, så att den "nya" sannolikheten för skuld (\(P(\text{skyldig} \mid \text{Bevis1})\))
                blir den "gamla" priorsannolikheten i nästa steg, när du matar in ytterligare bevis.
                """)

    # Här visar vi PDF-knappen om final_in_pct finns i sessionen
    if st.session_state.get("final_in_pct") is not None:
        final_in_pct = st.session_state["final_in_pct"]
        st.markdown("---")
        st.markdown("#### PDF-export")
        if st.button("Skapa PDF med resultat"):
            # Bygg en HTML-sträng
            html_code = f"""
            <html>
            <head>
              <meta charset='utf-8'>
              <style>
                body {{
                  font-family: Arial, sans-serif;
                }}
                .logo {{
                  margin-bottom: 20px;
                }}
                .header {{
                  font-size: 24px;
                  font-weight: bold;
                }}
                .datetime {{
                  font-size: 14px;
                  color: #666;
                }}
                table, th, td {{
                  border: 1px solid #ccc;
                  border-collapse: collapse;
                  padding: 8px;
                }}
              </style>
            </head>
            <body>
              <img src='lambertz_logo.png' class='logo' width='120' />
              <div class='header'>Lambertz Bevisvärdering</div>
              <div class='datetime'>Rapport genererad: {pd.Timestamp.now()}</div>

              <h2>Slutlig sannolikhet:</h2>
              <p><strong>{format_auto_decimals(final_in_pct)} %</strong> – {interpret_probability_in_words(final_in_pct)}</p>

              <p>Här kan du lägga till en mer detaljerad tabell eller sammanfattning.</p>
            </body>
            </html>
            """
            pdf_data = generate_pdf_report(html_code)
            if pdf_data:
                st.download_button(
                    label="Ladda ner PDF",
                    data=pdf_data,
                    file_name="rapport.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Kunde inte generera PDF. Kontrollera log och att wkhtmltopdf är installerat.")

    with colB:
        if st.button("Monte Carlo simulering (demo)"):
            if not st.session_state.get("widget_use_intervals", False):
                st.error("Intervall-läge måste vara aktiverat för Monte Carlo.")
            else:
                n_samples = 1000
                results = []
                for _ in range(n_samples):
                    post = prior
                    for (mina, maxa, minna, maxna) in bevis_data:
                        pba = random.uniform(mina, maxa)
                        pbna = random.uniform(minna, maxna)
                        num = pba*post
                        den = num + pbna*(1-post)
                        post = num/den if den != 0 else 0
                    if enable_negative_evidence and len(negative_bevis_data) > 0:
                        for (nbga, nbgna) in negative_bevis_data:
                            # Här slumpas inte nbga/nbgna, utan tas som single values
                            # men man kan även randomisera kring dem om man vill.
                            pba_neg = nbga
                            pbna_neg = nbgna
                            num2 = pba_neg * post
                            den2 = num2 + pbna_neg*(1-post)
                            post = num2/den2 if den2!=0 else 0
                    results.append(post*100)
                arr = np.array(results)
                medel = arr.mean()
                minv = arr.min()
                maxv = arr.max()
                stdv = arr.std()
                medianv = np.median(arr)

                st.write(f"**Monte Carlo** (antal={n_samples}):")
                st.write(
                    f"- Medel: {format_auto_decimals(medel)} %\n"
                    f"- Min: {format_auto_decimals(minv)} %\n"
                    f"- Max: {format_auto_decimals(maxv)} %\n"
                    f"- Std: {format_auto_decimals(stdv)}\n"
                    f"- Median: {format_auto_decimals(medianv)} %"
                )

                hist_data = pd.DataFrame({"Posterior (%)": arr})
                chart = alt.Chart(hist_data).mark_bar().encode(
                    x=alt.X("Posterior (%):Q", bin=alt.Bin(maxbins=30)),
                    y='count()'
                )
                st.altair_chart(chart, use_container_width=True)

                boxplot = alt.Chart(hist_data).mark_boxplot().encode(
                    y="Posterior (%):Q"
                )
                st.write("Box–plot:")
                st.altair_chart(boxplot, use_container_width=True)

                median_tolk = interpret_probability_in_words(medianv)
                st.info(f"**Monte Carlo**:\n"
                        f"Min={format_auto_decimals(minv)} %, Max={format_auto_decimals(maxv)} %, "
                        f"Median={format_auto_decimals(medianv)} % – tolkas som {median_tolk}.")

#########################################################################
# do_exact_bayes_calculation
#########################################################################
def do_exact_bayes_calculation(prior, bevis_data, use_intervals=False):
    """
    Om use_intervals=True returnerar vi tre listor: min-, median-, max-posterior.
    Annars returnerar vi en (posterior_list, row_list).
    """
    if use_intervals:
        min_post_list = [prior]
        median_post_list = [prior]
        max_post_list = [prior]
        current_min = prior
        current_median = prior
        current_max = prior

        for (mina, maxa, minna, maxna) in bevis_data:
            numerator_min = mina * current_min
            denominator_min = numerator_min + minna*(1 - current_min)
            new_min = numerator_min/denominator_min if denominator_min != 0 else 0
            min_post_list.append(new_min)
            current_min = new_min

            pba_med = (mina + maxa)/2
            pbna_med = (minna + maxna)/2
            numerator_med = pba_med * current_median
            denominator_med = numerator_med + pbna_med*(1 - current_median)
            new_med = numerator_med/denominator_med if denominator_med != 0 else 0
            median_post_list.append(new_med)
            current_median = new_med

            numerator_max = maxa * current_max
            denominator_max = numerator_max + maxna*(1 - current_max)
            new_max = numerator_max/denominator_max if denominator_max != 0 else 0
            current_max = new_max  # keep the code as is
            
        return (min_post_list, median_post_list, max_post_list)
    else:
        row_list = []
        posterior_list = [prior]
        current_posterior = prior
        i = 1
        for b in bevis_data:
            pba, pbna = b
            old_posterior = current_posterior
            numerator = pba * old_posterior
            denominator = numerator + pbna*(1 - old_posterior)
            new_posterior = numerator/denominator if denominator != 0 else 0

            delta = (new_posterior - old_posterior)*100
            new_post_percent = new_posterior*100

            if new_post_percent >= 95:
                kommentar = "Utom rimligt tvivel (>95%)"
            elif new_post_percent >= 80:
                kommentar = "Talar starkt för skuld (>80%)"
            elif new_post_percent >= 60:
                kommentar = "Tillräckliga skäl för åtal (>60%)"
            elif new_post_percent >= 50:
                kommentar = "Bevisövervikt(>50%)"
            elif new_post_percent >= 40:
                kommentar = "Sannolika skäl att misstänka (>40%)"
            elif new_post_percent >= 30:
                kommentar = "Tveksamt (>30%)"
            elif new_post_percent >= 20:
                kommentar = "Osannolikt (>20%)"
            else:
                kommentar = "Talar för oskuld (<20%)"

            row_list.append({
                "Bevis #": i,
                "P(B|A)": format_auto_decimals(pba*100),
                "P(B|¬A)": format_auto_decimals(pbna*100),
                "Gammal post. %": format_auto_decimals(old_posterior*100),
                "Ny post. %": format_auto_decimals(new_post_percent),
                "Förändring (pp)": format_auto_decimals(delta),
                "Kommentar": kommentar
            })
            current_posterior = new_posterior
            i += 1
            posterior_list.append(current_posterior)

        return (posterior_list, row_list)

#########################################################################
# 6) Bayesian Network
#########################################################################
def bayesian_network_demo():
    st.header("Bayesian Network (stjärnstruktur) – demo")
    st.markdown(r"""
    I en **stjärnstruktur**-modell har vi en nod \(S\) (skuld) 
    och \(n\) bevisnoder \(B_1..B_n\), antagna *conditionally independent* givet \(S\).
    """)

    with st.expander("Prior och antal bevis"):
        prior_percent = st.number_input(
            "Prior (%) för skuld (upp till 10 decimaler)",
            help="Sannolikhet i procent innan vi sett bevisen.",
            min_value=0.0,
            max_value=100.0,
            value=0.01,
            step=1e-7,
            format="%.9g"
        )
        p_s_true = prior_percent / 100.0
        p_s_false = 1 - p_s_true

        antal_bn = st.number_input(
            "Antal bevis (stjärnstruktur)",
            help="Hur många bevisnoder du vill mata in.",
            min_value=1,
            max_value=20,
            value=3,
            step=1
        )

    st.write("---")
    if st.button("Ladda exempelscenario (Bayesian Network)"):
        st.session_state["bn_s_0"] = 80.0
        st.session_state["bn_ns_0"] = 1.0
        st.session_state["bn_s_1"] = 60.0
        st.session_state["bn_ns_1"] = 20.0
        st.session_state["bn_s_2"] = 90.0
        st.session_state["bn_ns_2"] = 2.0
        st.info("Exempelscenario BN laddat (3 bevis)!")

    tabs_bn = st.tabs([f"Bevis {i+1}" for i in range(antal_bn)])
    bevis_bn = []
    for i in range(int(antal_bn)):
        with tabs_bn[i]:
            st.markdown("**P(B|S)**: sannolikhet för beviset om skyldig.")
            bn_s_key = f"bn_s_{i}"
            if bn_s_key not in st.session_state:
                st.session_state[bn_s_key] = 50.0
            p_true_given_s_percent = st.number_input(
                f"P(B{i+1}=true | S=true) i %",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state[bn_s_key],
                step=1e-7,
                format="%.9g",
                key=bn_s_key
            )

            st.markdown("**P(B|¬S)**: sannolikhet för beviset om oskyldig.")
            bn_ns_key = f"bn_ns_{i}"
            if bn_ns_key not in st.session_state:
                st.session_state[bn_ns_key] = 10.0
            p_true_given_ns_percent = st.number_input(
                f"P(B{i+1}=true | S=false) i %",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state[bn_ns_key],
                step=1e-7,
                format="%.9g",
                key=bn_ns_key
            )
            bevis_bn.append((p_true_given_s_percent/100.0, p_true_given_ns_percent/100.0))

    if st.button("Beräkna BN-stjärna"):
        product_if_s = 1.0
        for (pb_s, pb_ns) in bevis_bn:
            product_if_s *= pb_s
        top = p_s_true * product_if_s

        product_if_ns = 1.0
        for (pb_s, pb_ns) in bevis_bn:
            product_if_ns *= pb_ns
        bottom = top + p_s_false*product_if_ns

        if bottom == 0:
            posterior_bn = 0.0
        else:
            posterior_bn = top / bottom

        post_pct = posterior_bn * 100
        st.success(f"Posterior = {format_auto_decimals(post_pct)} % (om samtliga bevis är sanna)")
        fromtext = interpret_probability_in_words(post_pct)
        st.info(f"Bedömning: {fromtext} (≈ {format_auto_decimals(post_pct)} %)")

#########################################################################
# 7) Dempster–Shafer
#########################################################################
def dempster_shafer_demo():
    st.header("Dempster–Shafer (enkel demo)")
    st.markdown("""
    I Dempster–Shafer anger man massfunktioner m() för t.ex. {skyldig}, {oskuld}, {okänd}.
    Här en enkel variant med två bevis A och B,
    och vi räknar Dempsters rule of combination.
    """)

    with st.expander("Bevis A"):
        bA_skuld = st.slider("Mass (Bevis A) på 'skyldig'", 0.0, 1.0, 0.5, 0.01)
        bA_oskuld = st.slider("Mass (Bevis A) på 'oskuld'", 0.0, 1.0, 0.2, 0.01)
        if bA_skuld + bA_oskuld > 1.0:
            st.error("Summan kan ej överstiga 1. Justera värdena.")
            return
        bA_okand = 1.0 - (bA_skuld + bA_oskuld)

    with st.expander("Bevis B"):
        bB_skuld = st.slider("Mass (Bevis B) på 'skyldig'", 0.0, 1.0, 0.4, 0.01)
        bB_oskuld = st.slider("Mass (Bevis B) på 'oskuld'", 0.0, 1.0, 0.3, 0.01)
        if bB_skuld + bB_oskuld > 1.0:
            st.error("Summan kan ej överstiga 1. Justera värdena.")
            return
        bB_okand = 1.0 - (bB_skuld + bB_oskuld)

    if st.button("Kombinera med Dempster"):
        conflict = (bA_skuld * bB_oskuld) + (bA_oskuld * bB_skuld)
        K = 1.0 - conflict
        if K == 0:
            st.error("Total konflikt => K=0, kan ej kombineras.")
            return

        m_skyldig_num = (bA_skuld*bB_skuld) + (bA_skuld*bB_okand) + (bA_okand*bB_skuld)
        m_skyldig = m_skyldig_num / K

        m_oskuld_num = (bA_oskuld*bB_oskuld) + (bA_oskuld*bB_okand) + (bA_okand*bB_oskuld)
        m_oskuld = m_oskuld_num / K

        m_okand = 1.0 - (m_skyldig + m_oskuld)

        st.write("**Resultat av Dempsters rule**:")
        st.write(f"m(skyldig) = {format_auto_decimals(m_skyldig)}")
        st.write(f"m(oskuld)  = {format_auto_decimals(m_oskuld)}")
        st.write(f"m(okänd)   = {format_auto_decimals(m_okand)}")
        st.write(f"(conflict = {format_auto_decimals(conflict)}, K= {format_auto_decimals(K)})")

#########################################################################
# KÖR (sista anropet) - OBS: generate_pdf_report finns definierad innan.
#########################################################################
if __name__ == "__main__":
    main()

#########################################################################
# 8) PDF-EXPORTFUNKTION (NYTT) - Flyttad Högre Upp men bevarad Här i Kommentar
#########################################################################
# def generate_pdf_report(html_content: str) -> bytes:
#     """
#     Genererar en PDF från en HTML-sträng och returnerar PDF:en som bytes.
#     Kräver att pdfkit och wkhtmltopdf är installerade och i PATH.
#     """
#     try:
#         pdf_bytes = pdfkit.from_string(html_content, False)
#         return pdf_bytes
#     except Exception as e:
#         print("Fel vid generering av PDF:", e)
#         return b""
