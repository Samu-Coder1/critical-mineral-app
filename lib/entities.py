# Centralized ENTITIES mapping used by the app's generic admin handlers
ENTITIES = {
    'users': {
        'csv': 'users.csv', 'id':'UserID', 'fields':['UserID','Username','PasswordHash','RoleID','Email'], 'title':'Users'
    },
    'countries': {
        'csv':'countries.csv','id':'CountryID','fields':['CountryID','CountryName','GDP_BillionUSD','MiningRevenue_BillionUSD','KeyProjects'],'title':'Countries'
    },
    'minerals': {
        'csv':'minerals.csv','id':'MineralID','fields':['MineralID','MineralName','Description','MarketPriceUSD_per_tonne'],'title':'Minerals'
    },
    'sites': {
        'csv':'sites.csv','id':'SiteID','fields':['SiteID','SiteName','CountryID','MineralID','Latitude','Longitude','Production_tonnes'],'title':'Sites','selects':{'CountryID':('countries','CountryID','CountryName'),'MineralID':('minerals','MineralID','MineralName')}
    },
    'production': {
        'csv':'production_stats.csv','id':'StatID','fields':['StatID','Year','CountryID','MineralID','Production_tonnes','ExportValue_BillionUSD'],'title':'Production Stats','selects':{'CountryID':('countries','CountryID','CountryName'),'MineralID':('minerals','MineralID','MineralName')}
    }
}
