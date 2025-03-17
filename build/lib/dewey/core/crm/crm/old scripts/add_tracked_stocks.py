from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.stock import Base, TrackedStock

# Initial list of stocks to track
INITIAL_STOCKS = [
    {"symbol": "AGM", "name": "Farmer Mac", "isin": "US3131483063", "notes": "Is it problematic if we call our fanclub 'aparnaholics' or is #rameshistans better"},
    {"symbol": "CROX", "name": "Crocs", "isin": "US2270461096", "notes": "Heydude sales bottom?"},
    {"symbol": "MELI", "name": "Mercadolibre", "isin": "US58733R1023", "notes": "Latin america's e-commerce marketplace"},
    {"symbol": "ARE", "name": "Alexandria real estate", "isin": "US0152711091", "notes": "Life sciences campuses and early-stage investing"},
    {"symbol": "ECAT", "name": "BlackRock ESG Capital Allocation Term Trust", "isin": "US09262F1003", "notes": "Chose not to participate in action"},
    {"symbol": "VCISY", "name": "Vinci S.A.", "isin": "US9273201015", "notes": "Physical transit infrastructure - toll roads and airports"},
    {"symbol": "NTDOY", "name": "Nintendo", "isin": "US6544453037", "notes": "117 million annual users. so much ip. Structural nostalgia dividend. and they're legendary at hardware"},
    {"symbol": "BMI", "name": "Badger Meter", "isin": "US0565251081", "notes": "Sold off on a quarter that seemed pretty nice to me"},
    {"symbol": "AMAL", "name": "Amalgamated Financial", "isin": "US0226711010", "notes": "The official bank of labor at a 19% fcf yield?"},
    {"symbol": "DUOL", "name": "Duolingo", "isin": "US26603R1068", "notes": "One of the few compelling education positions"},
    {"symbol": "TEAF", "name": "Ecofin Sustainable and Social Impact Term Fund", "isin": "US27901F1093", "notes": "Closed end fund"},
    {"symbol": "AHH", "name": "Armada Hoffler", "isin": "US04208T1088", "notes": "key man risk in Lou Haddad, but great assets & attitude. Builds to leed standards"},
    {"symbol": "GMIIX", "name": "GMO-Usonian Japan Value Creation", "isin": None, "notes": "interesting"},
    {"symbol": "AGM PRG", "name": "Farmer Mac Preferreds", "isin": "US3131483063", "notes": "why did it take me this long to buy these"},
    {"symbol": "SKM", "name": "SK Telecom Co. Ltd.", "isin": "KR7017670001", "notes": "Compelling entry point for safe seeming asset"},
    {"symbol": "EMNT", "name": "PIMCO ETF Trust - Enhanced Short Maturity Active ESG ETF", "isin": None, "notes": ""},
    {"symbol": "EFGSY", "name": "Eiffage SA", "isin": "FR0000130452", "notes": "French construction services co with great cf yield"},
    {"symbol": "MID", "name": "American Century Mid Cap Growth Impact ETF", "isin": None, "notes": "Non-closet index - wow!"},
    {"symbol": "PLDGP", "name": "Prologis Preferreds", "isin": None, "notes": "Don't love the equity, but I love the duration on these prefs"},
    {"symbol": "PWR", "name": "Quanta Services", "isin": "US74762E1029", "notes": "The people who actually build the power infrastructure"},
    {"symbol": "NYCB", "name": "New York Community Bank", "isin": "US6494451031", "notes": "Loans looking like many will get paid @ par"},
    {"symbol": "AWEG", "name": "Alger Weatherbie Specialized Growth", "isin": None, "notes": ""},
    {"symbol": "CKHUY", "name": "CK Hutchison Holdings Limited", "isin": "KYG217651051", "notes": "Investor in ports & infrastructure"},
    {"symbol": "IIPR", "name": "Innovative Industrial Properties Inc", "isin": "US45781V1017", "notes": "Medical cannabis facilities"},
    {"symbol": "LMND", "name": "Lemonade", "isin": "US52567D1072", "notes": "Public benefit corp approaching the tuck-in acquisition zone for many incumbents"},
    {"symbol": "ZM", "name": "Zoom Communications Inc", "isin": "US98980L1017", "notes": "Generating a ton of cash, not diluting a ton - central os for meetings work"},
    {"symbol": "SUSC", "name": "iShares ESG Aware USD Corporate Bond ETF", "isin": None, "notes": "Sort of a placeholder sadly...."},
    {"symbol": "BDORY", "name": "Banco do Brasil S.A.", "isin": "BRBBASACNOR3", "notes": "Issuing slbs left and right...oh and it's growing revs 16% while cutting cost"},
    {"symbol": "FGROY", "name": "FirstGroup plc", "isin": "GB0003452173", "notes": "British rail operator @ 32% fcf yield"},
    {"symbol": "PASTF", "name": "OPmobility SE", "isin": "FR0000124570", "notes": "Electrified vehicles supplier"},
    {"symbol": "WBD", "name": "Webuild S.p.A.", "isin": "IT0003865570", "notes": "Green energy manufacturer located in Europe"},
    {"symbol": "KEGN", "name": "Kenya Electricity Generating Company PLC", "isin": "KE0000000547", "notes": "Would love to buy this fucker but bet we cant"},
    {"symbol": "CTTOF", "name": "CTT - Correios De Portugal S.A.", "isin": "PTCTT0AM0001", "notes": "might be basically impossible to purchase, but worth taking a punt"},
    {"symbol": "LI", "name": "Li Auto Inc", "isin": "US50202M1027", "notes": "EV in China, is it weird that I like it more after the 100% tarrrif?"},
    {"symbol": "BEEZ", "name": "Honeytree US Equity", "isin": None, "notes": "so many things i was thinking of nibbling on in here"},
    {"symbol": "HOVNP", "name": "Hovnanian Enterprises Pref Share", "isin": "US4424871121", "notes": "They've got the cash flow to support it, and yeilds have not reacted to cuts at all"},
    {"symbol": "MBNKP", "name": "Medallion Bank", "isin": None, "notes": "Yield resets to sofr+ 6.46% in april 2025"},
    {"symbol": "BLD", "name": "TopBuild", "isin": "US89055F1030", "notes": "Energy-efficient insulation"},
    {"symbol": "NVRI", "name": "Enviri Corporation", "isin": "US4158641070", "notes": "Overlevered, but interesting assets and possible PFAS tailwind"},
    {"symbol": "QCRH", "name": "QCR Holdings Inc", "isin": "US74727A1043", "notes": "Tax credit financing - iiiinteresting"},
    {"symbol": "ELF", "name": "e.l.f. Beauty", "isin": "US26856L1035", "notes": "no falling knife catching"},
    {"symbol": "CCB", "name": "Coastal Financial Corporation", "isin": "US19046P2092", "notes": "AYFKM - 27.71% fcf yeild?"},
    {"symbol": "DNZOF", "name": "Denso", "isin": "JP3551500006", "notes": "When toyota commits to leadership in green tech, this will be a thing"},
    {"symbol": "INGR", "name": "Ingredion", "isin": "US4571871023", "notes": "Transition to greatness?"},
    {"symbol": "SVNLY", "name": "Svenska Handelsbanken AB", "isin": "SE0007100599", "notes": "Compelling bank position - 68% fcf yield and ramping revs"},
    {"symbol": "PHG", "name": "Koninklijke Philips NV", "isin": "US5004723038", "notes": "View is clearer after the settlement... but what else lurks? She's got a heartbeat....."},
    {"symbol": "COCO", "name": "Vita Coco Company Inc", "isin": "US92846Q1076", "notes": "MNST / CELS / ETC . .."},
    {"symbol": "CIG", "name": "Companhia Energética de Minas Gerais", "isin": "BRCMIGACNOR6", "notes": "0.2086"},
    {"symbol": "UNFI", "name": "United Natural Foods Inc.", "isin": "US9111631035", "notes": ""},
    {"symbol": "BYDDF", "name": "BYD Company", "isin": "CNE100000296", "notes": "Chinese EV"},
    {"symbol": "DNNGY", "name": "Orsted A S Unsponsored ADR", "isin": "US68750L1026", "notes": "I think I got a little too excited about the availability of ADRs for trading"},
    {"symbol": "BFS", "name": "Saul Centers Inc", "isin": "US8043951016", "notes": "DC-Centric community REIT with a challenged dividend"},
    {"symbol": "OMCL", "name": "Omnicell Inc", "isin": "US68213N1090", "notes": "Pharmacy systems & 'medication adherence' promoting packaging"},
    {"symbol": "HAFC", "name": "Hanmi Financial Corporation", "isin": "US4104952043", "notes": "Bank for korean-american immigrants"},
    {"symbol": "HUM", "name": "Humana Inc", "isin": "US4448591028", "notes": "Medicare advantage plan provider"},
    {"symbol": "LKQ", "name": "LKQ Corporation", "isin": "US5018892084", "notes": "Auto parts recycling"},
    {"symbol": "ENS", "name": "EnerSys", "isin": "US29275Y1029", "notes": "'stored energy' batteries for non-ev mobility, defense involvement"},
    {"symbol": "SEEFX", "name": "Saturna Sustainable Equity", "isin": None, "notes": "teeny & 1k minimum"},
    {"symbol": "ROOT", "name": "Root Inc", "isin": "US77664L2079", "notes": "D2c Insurance"},
    {"symbol": "UHS", "name": "Universal Health Services Inc", "isin": "US9139031002", "notes": "Stable growth and disrupted valuation - near-term oppty?"},
    {"symbol": "NLY", "name": "Annaly Capital Management, Inc.", "isin": "US0357108390", "notes": "Right at book value"},
    {"symbol": "YAHOY", "name": "Yahoo Japan + Line messeng", "isin": "JP3933800009", "notes": "Net Net"},
    {"symbol": "IMKTA", "name": "Ingles Markets Incorporated", "isin": None, "notes": ""},
    {"symbol": "FBMS", "name": "First Bancshares Inc", "isin": "US3189161033", "notes": "CDFI - one of the largest"},
    {"symbol": "LC", "name": "LendingClub", "isin": "US52603A2087", "notes": "Is LC actually… a net net right now?"},
    {"symbol": "CPRT", "name": "Copart Inc", "isin": "US2172041061", "notes": "Is mgmt focus on cost leading to retention/turnover issues?"},
    {"symbol": "IIF", "name": "The India Fund (MS)", "isin": "US61745C1053", "notes": "diversified india at a discount. TYSM"},
    {"symbol": "ALOT", "name": "AstroNova", "isin": "US04638F1084", "notes": "Printing - CFO +"},
    {"symbol": "CAAP", "name": "Corporacion America Airports SA", "isin": "LU1756447840", "notes": "Airports in latin america"},
    {"symbol": "AGX", "name": "Argan Inc.", "isin": "US04010E1091", "notes": "A mini quanta"},
    {"symbol": "HUBG", "name": "Hub Group", "isin": "US4433201062", "notes": "Intermodal rail"},
    {"symbol": "VTR", "name": "Ventas Inc", "isin": "US92276F1003", "notes": "Light on impact - Vibe still sketchy - but compelling asset base"},
    {"symbol": "TCLAF", "name": "Transcontinental Inc.", "isin": "CA8935781044", "notes": "Packaging - plastic to flyers"},
    {"symbol": "DNKEY", "name": "Danske Bank A/S", "isin": "DK0010274414", "notes": "0.2549"},
    {"symbol": "TV", "name": "Grupo Televisa S.A.B.", "isin": "MXP4987V1378", "notes": "social impact case hard"},
    {"symbol": "LII", "name": "Lennox International Inc", "isin": "US5261071071", "notes": "cold weather heat pumps"},
    {"symbol": "BRX", "name": "Brixmor REIT", "isin": "US11120U1051", "notes": "Grocery-anchored REIT"},
    {"symbol": "TTEK", "name": "Tetra Tech Inc", "isin": "US88162G1031", "notes": "water-related consulting services"},
    {"symbol": "WINA", "name": "Winmark Corp", "isin": "US9742501029", "notes": "Asset-light franchisor of plato's closet, play it again sports, and other circular economy stuffs"},
    {"symbol": "WTS", "name": "Watts Water Technologies Inc", "isin": "US9427491025", "notes": "Think we need to put in a cagefight with BMI"},
    {"symbol": "DDOG", "name": "DataDog", "isin": "US23804L1035", "notes": "Cloud monitoring & share based comp"},
    {"symbol": "FTNT", "name": "Fortinet", "isin": "US34959E1091", "notes": "Solid long-term growth roadmap"},
    {"symbol": "MTB", "name": "M&t Bank Corp", "isin": "US55261F1049", "notes": "Stable, conservatively run"},
    {"symbol": "AMT", "name": "American Tower Corp", "isin": "US03027X1000", "notes": "I'm content to sit this sector out until we understand the lead liability"},
    {"symbol": "PECO", "name": "Phillips Edison & Co Inc", "isin": "US71844V2016", "notes": "Grocery-anchored shopping centers"},
    {"symbol": "AME", "name": "Ametek Inc", "isin": "US0311001004", "notes": "Electric sensors with non-lethal defense applications"},
    {"symbol": "SBAC", "name": "SBA Communications Corp", "isin": "US78410G1040", "notes": "Shareholder yield is paltry compared to amt"},
    {"symbol": "ISNPY", "name": "INTESA SANPAOLO SPA", "isin": "IT0000072618", "notes": "Italian banking"},
    {"symbol": "JSTC", "name": "Adasina Social Justice All Cap Global ETF", "isin": None, "notes": ""},
    {"symbol": "HDSN", "name": "Hudson Technologies, Inc.", "isin": "US4441441098", "notes": "Refrigerant Management tech - buying window coming soon"}
]

def setup_db():
    engine = create_engine('postgresql+psycopg2://postgres:password@db:5432/postgres')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

def add_stocks():
    session = setup_db()
    
    for stock_info in INITIAL_STOCKS:
        # Check if stock already exists
        existing = session.query(TrackedStock).filter_by(symbol=stock_info["symbol"]).first()
        if not existing:
            stock = TrackedStock(
                symbol=stock_info["symbol"],
                name=stock_info["name"],
                isin=stock_info["isin"],
                notes=stock_info["notes"],
                added_date=datetime.utcnow(),
                is_active=True
            )
            session.add(stock)
    
    session.commit()
    session.close()

if __name__ == "__main__":
    add_stocks() 