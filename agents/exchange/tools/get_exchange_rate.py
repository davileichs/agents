import requests
import xml.etree.ElementTree as ET

def get_exchange_rate(base_currency: str, target_currency: str) -> str:
    """Fetches the latest exchange rate from EUR to the target currency using ECB."""
    base_currency = base_currency.upper()
    target_currency = target_currency.upper()
    
    if base_currency == target_currency:
        return f"The exchange rate for {base_currency} to {target_currency} is 1.0"
        
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return f"Error connecting to ECB: Status {response.status_code}"
            
        root = ET.fromstring(response.content)
        # XML Namespace used by ECB:
        namespaces = {'ex': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
        
        # Traverse to the Cube containing the currencies
        cubes = root.findall('.//ex:Cube[@currency]', namespaces)
        
        rates = {'EUR': 1.0}
        for cube in cubes:
            curr = cube.attrib.get('currency')
            rate_val = cube.attrib.get('rate')
            if curr and rate_val:
                rates[curr] = float(rate_val)
                
        if base_currency not in rates:
            return f"Base currency {base_currency} not found in ECB daily rates."
        if target_currency not in rates:
            return f"Target currency {target_currency} not found in ECB daily rates."
            
        base_rate = rates[base_currency]
        target_rate = rates[target_currency]
        
        # Calculate cross rate. Since ECB gives 1 EUR = X CUR.
        # So 1 EUR = base_rate BASE_CUR, 1 EUR = target_rate TARGET_CUR
        # Therefore, 1 BASE_CUR = (target_rate / base_rate) TARGET_CUR
        final_rate = target_rate / base_rate
        
        return f"The latest ECB exchange rate is 1 {base_currency} = {final_rate:.4f} {target_currency}."
            
    except Exception as e:
        return f"Request failed: {str(e)}"
