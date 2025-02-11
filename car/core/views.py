from django.shortcuts import render,redirect
import json
import pandas as pd
import requests
import pandas as pd
import time
from random import randint
import datetime
import json
from collections import OrderedDict
import os
from django.db.models import Q
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import urllib.parse
from django.http import JsonResponse
from .models import *
from django.contrib import messages
from django.core.paginator import Paginator

BASE_URL = "https://www.carwale.com/api/makepagedata/"
BASE_URL_Model = "https://www.carwale.com/api/modelpagedata/"
VERSION_URL = "https://www.carwale.com/api/v3/versions/"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_FILE_PATH = os.path.join(BASE_DIR, 'core', 'config.json')



with open(JSON_FILE_PATH, 'r') as file:
    file_data = json.load(file)





gst_rate = file_data.get("gst")




five_engine_1000 = file_data.get('5').get("engine_capacity").get("less_1000")
five_engine_1500 = file_data.get('5').get("engine_capacity").get("less_1500")
five_engine_else = file_data.get('5').get("engine_capacity").get("else")
ten_engine_1000 = file_data.get('10').get("engine_capacity").get("less_1000")
ten_engine_1500 = file_data.get('10').get("engine_capacity").get("less_1500")
ten_engine_else = file_data.get('10').get("engine_capacity").get("else")
last_engine_1000 = file_data.get('15').get("engine_capacity").get("less_1000")
last_engine_1500 = file_data.get('15').get("engine_capacity").get("less_1500")
last_engine_else = file_data.get('15').get("engine_capacity").get("else")

engine_capacity_1000 = file_data.get("engine_capacity_1000")
engine_capacity_1500 = file_data.get("engine_capacity_1500")
engine_capacity_else = file_data.get("engine_capacity_greater")



def extract_engine(brand_name, model_name, city_id,versionsid, platform_id=1, retries=3):
    print("Initial Brand Name:", brand_name)
    print("version id",versionsid)
    if " " in brand_name:   
        brand_name= brand_name.replace(" ","-")
    print("Model Masking Name:", model_name)
    if " " in model_name:   
        model_name= model_name.replace(" ","-")
    brand_name=brand_name.lower()
    model_name=model_name.lower()
    params = {
        "makeMaskingName": brand_name,
        "modelMaskingName": model_name,
        "cityId": city_id,
        "areaId": -1,
        "showOfferUpfront": "false",
        "platformId": platform_id
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(BASE_URL_Model, headers=headers, params=params)
            response.raise_for_status()  
            responses = response.json()
            def get_specs_summary(response, version_id):
                for version in response.get("versions", []):
                    if version.get("versionId") == version_id:
                        return version.get("specsSummary", [])
                return None
            version_dataa = get_specs_summary(responses, versionsid)
            if version_dataa[0]['unitType'] == 'cc':
                result=f"{version_dataa[0]['value']} cc"
            elif version_dataa[0]['unitType'] == 'kWh':
                result=f"{version_dataa[0]['value']} kWh"
            return result
        except requests.exceptions.RequestException as e:
            attempt += 1
            if attempt < retries:
                wait_time = randint(1, 3)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Failed to fetch data after {retries} attempts.")
                return None


def fetch_variant_data(model_id, city_id, retries=5):
    params = {
        "modelId": model_id,
        "type": "new",  
        "itemIds": "29,26",  
        "cityId": city_id,
        "application": 1
    }
    print("Fetching variant data for model ID:", model_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(VERSION_URL, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            attempt += 1
            if attempt < retries:
                wait_time = randint(1, 3)
                time.sleep(wait_time)
            else:
                return None


def extract_models_to_df(brand_name, brand_data, city_id):
    city_mapping = {
        1: "Mumbai",
        105: "Bangalore"
    }
    city_name = city_mapping.get(city_id, f"{city_id}")  
    print("city name --------> ", city_name)
    if 'models' in brand_data:
        models = []
        for model in brand_data.get('models'):
            model_name = model.get('offerDetails', {}).get('ModelName', None)
            model_masking_name=model.get('modelMaskingName')
            model_id = model.get('modelId', None)
            model_price = model.get('offerDetails', {}).get('formattedPrice', None)
            model_features = model.get('offerDetails', {}).get('priceLabel', None)
            if model_name and model_id:
                variant_data = fetch_variant_data(model_id, city_id)
                variants = []
                for variant in variant_data.get('variants', []):
                    version_name = variant.get('versionName', None)
                    version_id = variant.get('versionId', None)
                    engine_data= extract_engine(brand_name,model_masking_name,city_id,version_id)
                    transmission = next((spec['value'] for spec in variant.get('specsSummary', []) if spec['itemName'] == 'Transmission Type'), None)
                    fuel_type = next((spec['value'] for spec in variant.get('specsSummary', []) if spec['itemName'] == 'Fuel Type'), None)
                    price = variant.get('priceOverview', {}).get('formattedPrice', None)  # Example price field
                    exshowroomprice = variant.get('priceOverview', {}).get('exShowRoomPrice', None)  # Example price field
                    features = variant.get('features', None)
                    if version_name and version_id:
                        variants.append({
                            'Brand Name': brand_name,
                            'Model Name': model_name,
                            'Model ID': model_id,
                            'City': city_name,
                            'Variant Name': version_name,
                            'Version ID': version_id,
                            'Transmission Type': transmission,
                            'Fuel Type': fuel_type,
                            'Ex-Showroom Price':exshowroomprice,
                            'On-Road Price': price,
                            'cc':engine_data
                        })
                if variants:
                    models.extend(variants)
        df = pd.DataFrame(models)
        print("___**",df)
        return df
    else:
        print(f"No models data found for brand '{brand_name}'.")
        return None
    



def fetch_model_data(brand_name, city_id, platform_id=1, retries=3):
    params = {
        "maskingName": brand_name,
        "cityId": city_id,
        "areaId": -1,
        "platformId": platform_id
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(BASE_URL, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            attempt += 1
            if attempt < retries:
                wait_time = randint(1, 3)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Retry failed, adjusting brand_name...")
                brand_name = brand_name.lower().replace(" ", "-")
                print("Adjusted Brand Name:", brand_name)
                params["maskingName"] = brand_name
                attempt = 0  
                continue
    print(f"Failed to fetch data after {retries} attempts.")
    return None



def home(request):
    return render(request,'index.html')


def fetch_models(request):
    data = json.loads(request.body)
    city_id = float(data.get('city_id'))
    selected_brands = data.get('brands', [])
    all_models_data = []
    if True:
        for brand_name in selected_brands:
            brand_data = fetch_model_data(brand_name, city_id)
            print('brand data -------> ',brand_data)
            if brand_data:
                df = extract_models_to_df(brand_name, brand_data, city_id)
                if df is not None:
                    all_models_data.append(df)
        if all_models_data:
            final_df = pd.concat(all_models_data, ignore_index=True)
            print({
                'success': True,
                'file_path': f'',
                'data': final_df.to_dict(orient='records')  # Return data for preview
            })
            return JsonResponse({
                'success': True,
                'file_path': f'',
                'data': final_df.to_dict(orient='records')  
            })
        else:
            return JsonResponse({'success': False, 'message': 'No data found for the selected brands.'})
    else: 
        return JsonResponse({'success': False, 'message': str(e)})


def get_brand_names():
        brand_names = ['Maruti Suzuki', 'Mahindra', 'Tata', 'Toyota', 'BMW', 'Hyundai', 'Mercedes-Benz', 'Kia', 'Audi', 'Skoda', 'MG', 'Land Rover', 'Porsche', 'Lamborghini', 'Volvo', 'Honda', 'Citroen', 'Volkswagen', 'Ferrari', 'Renault', 'Lexus', 'Maserati', 'Jeep', 'Jaguar', 'Rolls-Royce', 'BYD', 'MINI', 'Nissan', 'Aston Martin', 'McLaren', 'Isuzu', 'VinFast', 'Force Motors', 'Bentley', 'Tesla', 'Lotus', 'Fisker', 'Pravaig', 'OLA', 'Leapmotor'] 
        return brand_names


def fetch_brands(request):
    if True:
        brand_names = get_brand_names()
        return JsonResponse({'success': True, 'brands': brand_names})
    else: 
        return JsonResponse({'success': False, 'message': str(e)})

def calculate_vehicle_age(manufacture_year):
    current_year = datetime.datetime.now().year
    print("current_year",current_year)
    print("manufacture_year",manufacture_year)
    print("vehicle_age",current_year - manufacture_year)
    return current_year - manufacture_year

def calculate_factor_rate(idv, vehicle_age, engine_capacity):
    if vehicle_age <= 5:
        if engine_capacity <= 1000:
            rate = five_engine_1000
        elif engine_capacity <= 1500:
            rate = five_engine_1500
        else:
            rate = five_engine_else
    elif 5 < vehicle_age <= 10:
        if engine_capacity <= 1000:
            rate = ten_engine_1000
        elif engine_capacity <= 1500:
            rate = ten_engine_1500
        else:
            rate = ten_engine_else
    else:
        if engine_capacity <= 1000:
            rate = last_engine_1000
        elif engine_capacity <= 1500:
            rate = last_engine_1500
        else:
            rate = last_engine_else


    factor_rate_Tata_Aig = (idv["Tata_Aig"][0]['idv'] * rate) / 100
    for key in idv.keys():
        if key == 'Tata_Aig':
            idv[key].append({"rate":rate})
        elif key == 'liberty_gic':
            idv[key].append({"rate":rate})
        elif key == 'hdfc_ergo':
            idv[key].append({"rate":rate})
        elif key == 'icici_lombard':
            idv[key].append({"rate":rate})
    for key in idv.keys():
        if key == 'Tata_Aig':
            idv[key].append({"od_premium":round(factor_rate_Tata_Aig)})
        elif key == 'liberty_gic':
            idv[key].append({"od_premium":round(factor_rate_Tata_Aig)})
        elif key == 'hdfc_ergo':
            idv[key].append({"od_premium":round(factor_rate_Tata_Aig)})
        elif key == 'icici_lombard':
            idv[key].append({"od_premium":round(factor_rate_Tata_Aig)})
    return idv

def ncb_rate_percentage(vehicle_age,previous_claim,idv):
    print("vehicle_age",vehicle_age)
    print("previous_claim",previous_claim)
    ncb_rate = float(previous_claim)
    for key in idv.keys():
        if key == 'Tata_Aig':
            idv[key].append({"ncb_rate":ncb_rate})
        elif key == 'liberty_gic':
            idv[key].append({"ncb_rate":ncb_rate})
        elif key == 'hdfc_ergo':
            idv[key].append({"ncb_rate":ncb_rate})
        elif key == 'icici_lombard':
            idv[key].append({"ncb_rate":ncb_rate})
    return idv


def ncb_calculation(vehicle_age, od_premium):
    od_premium_tata = od_premium["Tata_Aig"][2]['od_premium']
    od_premium_liberty = od_premium["liberty_gic"][2]['od_premium']
    od_premium_hdfc = od_premium["hdfc_ergo"][2]['od_premium']
    od_premium_icici = od_premium["icici_lombard"][2]['od_premium']
    ncb_rate_tata = od_premium["Tata_Aig"][3]['ncb_rate']
    ncb_rate_liberty = od_premium["liberty_gic"][3]['ncb_rate']
    ncb_rate_hdfc = od_premium["hdfc_ergo"][3]['ncb_rate']
    ncb_rate_icici = od_premium["icici_lombard"][3]['ncb_rate']

    
    if vehicle_age > 0:
        ncb_tata = od_premium_tata * (ncb_rate_tata / 100)
        ncb_liberty = od_premium_liberty * (ncb_rate_liberty / 100)
        ncb_hdfc = od_premium_hdfc * (ncb_rate_hdfc / 100)
        ncb_icici = od_premium_icici * (ncb_rate_icici / 100)
    else:
        ncb_tata = 0
        ncb_liberty = 0
        ncb_hdfc = 0
        ncb_icici = 0
    for key in od_premium.keys():
        if key == 'Tata_Aig':
            od_premium[key].append({"ncb":round(ncb_tata)})
        elif key == 'liberty_gic':
            od_premium[key].append({"ncb":round(ncb_liberty)})
        elif key == 'hdfc_ergo':
            od_premium[key].append({"ncb":round(ncb_hdfc)})
        elif key == 'icici_lombard':
            od_premium[key].append({"ncb":round(ncb_icici)})
    return od_premium

def after_ncb(od_premium):
    od_premium_tata = od_premium["Tata_Aig"][2]['od_premium']
    od_premium_liberty = od_premium["liberty_gic"][2]['od_premium']
    od_premium_hdfc = od_premium["hdfc_ergo"][2]['od_premium']
    od_premium_icici = od_premium["icici_lombard"][2]['od_premium']
    ncb_tata = od_premium["Tata_Aig"][4]['ncb']
    ncb_liberty = od_premium["liberty_gic"][4]['ncb']
    ncb_hdfc = od_premium["hdfc_ergo"][4]['ncb']
    ncb_icici = od_premium["icici_lombard"][4]['ncb']
    if ncb_tata > 0:
        after_ncb_tata = od_premium_tata - ncb_tata
    else:
        after_ncb_tata = od_premium_tata
    if ncb_liberty > 0:
        after_ncb_liberty = od_premium_liberty - ncb_liberty
    else:
        after_ncb_liberty = od_premium_liberty
    if ncb_hdfc > 0:
        after_ncb_hdfc = od_premium_hdfc - ncb_hdfc
    else:
        after_ncb_hdfc = od_premium_hdfc
    if ncb_icici > 0:
        after_ncb_icici = od_premium_icici - ncb_icici
    else:
        after_ncb_icici = od_premium_icici
    for key in od_premium.keys():
        if key == 'Tata_Aig':
            od_premium[key].append({"after_ncb":round(after_ncb_tata)})
        elif key == 'liberty_gic':
            od_premium[key].append({"after_ncb":round(after_ncb_liberty)})
        elif key == 'hdfc_ergo':
            od_premium[key].append({"after_ncb":round(after_ncb_hdfc)})
        elif key == 'icici_lombard':
            od_premium[key].append({"after_ncb":round(after_ncb_icici)})
    return od_premium


def discount_rate_amount(after_ncb, discount_ratetata, discount_rateliberty, discount_ratehdfc, discount_rateicici):
    after_ncb_tata = after_ncb["Tata_Aig"][5]['after_ncb']
    after_ncb_liberty = after_ncb["liberty_gic"][5]['after_ncb']
    after_ncb_hdfc = after_ncb["hdfc_ergo"][5]['after_ncb']
    after_ncb_icici = after_ncb["icici_lombard"][5]['after_ncb']
    discount_rate_tata = after_ncb_tata * (discount_ratetata / 100)
    discount_rate_liberty = after_ncb_liberty * (discount_rateliberty / 100)
    discount_rate_hdfc = after_ncb_hdfc * (discount_ratehdfc / 100)
    discount_rate_icici = after_ncb_icici * (discount_rateicici / 100)
    for key in after_ncb.keys():
        if key == 'Tata_Aig':
            after_ncb[key].append({"discount_rate":round(discount_ratetata)})
            after_ncb[key].append({"discount_Amount":round(discount_rate_tata)})
        elif key == 'liberty_gic':
            after_ncb[key].append({"discount_rate":round(discount_rateliberty)})
            after_ncb[key].append({"discount_Amount":round(discount_rate_liberty)})
        elif key == 'hdfc_ergo':
            after_ncb[key].append({"discount_rate":round(discount_ratehdfc)})
            after_ncb[key].append({"discount_Amount":round(discount_rate_hdfc)})
        elif key == 'icici_lombard':
            after_ncb[key].append({"discount_rate":round(discount_rateicici)})
            after_ncb[key].append({"discount_Amount":round(discount_rate_icici)})
    return after_ncb

def premium_amount(discount_rate_amount):
    discount_rate_amount_tata = discount_rate_amount["Tata_Aig"][7]['discount_Amount']
    discount_rate_amount_liberty = discount_rate_amount["liberty_gic"][7]['discount_Amount']
    discount_rate_amount_hdfc = discount_rate_amount["hdfc_ergo"][7]['discount_Amount']
    discount_rate_amount_icici = discount_rate_amount["icici_lombard"][7]['discount_Amount']
    ncb_amount_tata = discount_rate_amount["Tata_Aig"][4]['ncb']
    ncb_amount_liberty = discount_rate_amount["liberty_gic"][4]['ncb']
    ncb_amount_hdfc = discount_rate_amount["hdfc_ergo"][4]['ncb']
    ncb_amount_icici = discount_rate_amount["icici_lombard"][4]['ncb']
    od_premium_tata = discount_rate_amount["Tata_Aig"][2]['od_premium']
    od_premium_liberty = discount_rate_amount["liberty_gic"][2]['od_premium']
    od_premium_hdfc = discount_rate_amount["hdfc_ergo"][2]['od_premium']
    od_premium_icici = discount_rate_amount["icici_lombard"][2]['od_premium']
    premium_amount_tata = od_premium_tata - ncb_amount_tata - discount_rate_amount_tata
    premium_amount_liberty = od_premium_liberty - ncb_amount_liberty - discount_rate_amount_liberty
    premium_amount_hdfc = od_premium_hdfc - ncb_amount_hdfc - discount_rate_amount_hdfc
    premium_amount_icici = od_premium_icici - ncb_amount_icici - discount_rate_amount_icici
    for key in discount_rate_amount.keys():
        if key == 'Tata_Aig':
            discount_rate_amount[key].append({"premium_amount":round(premium_amount_tata)})
        elif key == 'liberty_gic':
            discount_rate_amount[key].append({"premium_amount":round(premium_amount_liberty)})
        elif key == 'hdfc_ergo':
            discount_rate_amount[key].append({"premium_amount":round(premium_amount_hdfc)})
        elif key == 'icici_lombard':
            discount_rate_amount[key].append({"premium_amount":round(premium_amount_icici)})
    return discount_rate_amount

def third_party_premium(vehicle_age,engine_capacity,premium_amount):
    print("vehicle_age",vehicle_age)
    print("engine_capacity",engine_capacity)
    print("premium_amount",premium_amount)
    if vehicle_age > 3:
        if engine_capacity <= 1000:
            rate = engine_capacity_1000
        elif 1000<= engine_capacity <= 1500:
            rate = engine_capacity_1500
        else:
            rate = engine_capacity_else
    else:
        rate = 0
    for key in premium_amount.keys():
        if key == 'Tata_Aig':
            premium_amount[key].append({"third_party":rate})
        elif key == 'liberty_gic':
            premium_amount[key].append({"third_party":rate})
        elif key == 'hdfc_ergo':
            premium_amount[key].append({"third_party":rate})
        elif key == 'icici_lombard':
            premium_amount[key].append({"third_party":rate})

    return premium_amount


def owner_driver_cover(vehicle_age,third_party_premium):
    if vehicle_age > 3:
        driver_cover_tata= 375
        driver_cover_liberty= 375
        driver_cover_hdfc= 325
        driver_cover_icici= 675
        for key in third_party_premium.keys():
            if key == 'Tata_Aig':
                third_party_premium[key].append({"driver_cover":driver_cover_tata})
            elif key == 'liberty_gic':
                third_party_premium[key].append({"driver_cover":driver_cover_liberty})
            elif key == 'hdfc_ergo':
                third_party_premium[key].append({"driver_cover":driver_cover_hdfc})
            elif key == 'icici_lombard':
                third_party_premium[key].append({"driver_cover":driver_cover_icici})
    else:
        driver_cover= 0
        for key in third_party_premium.keys():
            if key == 'Tata_Aig':
                third_party_premium[key].append({"driver_cover":driver_cover})
            elif key == 'liberty_gic':
                third_party_premium[key].append({"driver_cover":driver_cover})
            elif key == 'hdfc_ergo':
                third_party_premium[key].append({"driver_cover":driver_cover})
            elif key == 'icici_lombard':
                third_party_premium[key].append({"driver_cover":driver_cover})
    
    return third_party_premium


def calculate_idv(vehicle_cost, vehicle_age,dic):
    depreciation_rates = {
        1: 10,
        2: 20,
        3: 30,
        4: 40,
        5: 50
    }
    print('vehicle_age',vehicle_age)

    depreciation_rate = depreciation_rates.get(vehicle_age, 50)
    print('depreciation_rate',depreciation_rate)
    depreciation_amount = (depreciation_rate / 100) * vehicle_cost
    idv = vehicle_cost - depreciation_amount
    for key in dic.keys():
        if key == 'Tata_Aig':
            dic[key].append({"idv":idv})
        elif key == 'liberty_gic':
            dic[key].append({"idv":idv})
        elif key == 'hdfc_ergo':
            dic[key].append({"idv":idv})
        elif key == 'icici_lombard':
            dic[key].append ({"idv":idv})
    return dic



def paid_driver_cover(vehicle_age,owner_driver_cover_result):
    if vehicle_age > 3:
        paid_driver_cover= 50
    else:
        paid_driver_cover= 0
    for key in owner_driver_cover_result.keys():
        if key == 'Tata_Aig':
            owner_driver_cover_result[key].append({"paid_driver_cover":paid_driver_cover})
        elif key == 'liberty_gic':
            owner_driver_cover_result[key].append({"paid_driver_cover":paid_driver_cover})
        elif key == 'hdfc_ergo':
            owner_driver_cover_result[key].append({"paid_driver_cover":paid_driver_cover})
        elif key == 'icici_lombard':
            owner_driver_cover_result[key].append({"paid_driver_cover":paid_driver_cover})
    return owner_driver_cover_result


def paid_passenger_cover(paid_driver_cover_result):
    paid_passenger_cover_liberty= 250
    paid_passenger_cover_hdfc= 0
    paid_passenger_cover_icici= 0
    for key in paid_driver_cover_result.keys():
        if key == 'Tata_Aig':
            paid_driver_cover_result[key].append({"paid_passenger_cover":0})
        elif key == 'liberty_gic':
            paid_driver_cover_result[key].append({"paid_passenger_cover":paid_passenger_cover_liberty})
        elif key == 'hdfc_ergo':
            paid_driver_cover_result[key].append({"paid_passenger_cover":paid_passenger_cover_hdfc})
        elif key == 'icici_lombard':
            paid_driver_cover_result[key].append({"paid_passenger_cover":paid_passenger_cover_icici})
    return paid_driver_cover_result

def bumper_to_bumper(brand_name, varian_name,paid_passenger_cover_result,year):
    print("bumper to bumper-------------------")
    print("brand_name",brand_name)
    print("varian_name",varian_name)
    
    with open("sheets_data.json", 'r') as file:
        data = json.load(file)
    Tata_aig = data.get('TATA AIG', {})
    library_gic = data.get('LIBERTY', {})
    hdfc_ergo = data.get('HDFC', {})
    icici_lombard = data.get('ICICI', {})
    varian_name=varian_name.lower()
    result_data_tata = Brand.objects.filter(
        Q(name__icontains=brand_name) | Q(name__icontains=brand_name.split()[0]),
        model__icontains=varian_name,
        insurance_company='TATA AIG',
        year=year
    ).order_by('-id').first()
    
    print("###########################################################################################################", result_data_tata)
    
    result_data_hdfc = Brand.objects.filter(
        Q(name__icontains=brand_name) | Q(name__icontains=brand_name.split()[0]),
        model__icontains=varian_name,
        insurance_company='HDFC',
        year=year
    ).order_by('-id').first()
    
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$", result_data_hdfc)
    
    result_data_icici = Brand.objects.filter(
        Q(name__icontains=brand_name) | Q(name__icontains=brand_name.split()[0]),
        model__icontains=varian_name,
        insurance_company='ICICI',
        year=year
    ).order_by('-id').first()
    
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", result_data_icici)
    
    result_data_liberty = Brand.objects.filter(
        Q(name__icontains=brand_name) | Q(name__icontains=brand_name.split()[0]),
        model__icontains=varian_name,
        insurance_company='LIBERTY',
        year=year
    ).order_by('-id').first()
    
    print("***********************************************************************************************************", result_data_liberty)
    # result_tata = [item for item in Tata_aig if (str(brand_name).lower() in item["MAKE"].lower() or item['MAKE'].lower() in str(brand_name).lower()) and (str(varian_name).lower() in item["MODEL"].lower() or item['MODEL'].lower() in str(varian_name).lower())]
    # result_liberty = [item for item in library_gic if (str(brand_name).lower() in item["MAKE"].lower() or item['MAKE'].lower() in str(brand_name).lower()) and (str(varian_name).lower() in item["MODEL"].lower() or item['MODEL'].lower() in str(varian_name).lower())]
    # result_hdfc = [item for item in hdfc_ergo if (str(brand_name).lower() in item["MAKE"].lower() or item['MAKE'].lower() in str(brand_name).lower()) and (str(varian_name).lower() in item["MODEL"].lower() or item['MODEL'].lower() in str(varian_name).lower())]
    # result_icici = [item for item in icici_lombard if (str(brand_name).lower() in item["MAKE"].lower() or item['MAKE'].lower() in str(brand_name).lower()) and (str(varian_name).lower() in item["MODEL"].lower() or item['MODEL'].lower() in str(varian_name).lower())]
    # print("result_tata",result_tata)
    # print("result_liberty",result_liberty) 
    # print("result_hdfc",result_hdfc)
    # print("result_icici",result_icici)

    # if len(result_data_tata) != 0:
    if result_data_tata:
        # zd=result_tata[0]['ZD']
        # con=result_tata[0]['CON']
        # engine_cover=result_tata[0]['ENGINE']
        # tyre=result_tata[0]['TYRE']
        # rti=result_tata[0]['RTI']
        zd = float(result_data_tata.zd)
        con = float(result_data_tata.con)
        engine_cover = float(result_data_tata.engine)
        tyre = float(result_data_tata.tyre)
        rti = float(result_data_tata.rti)
        print("!@!@!@!@!!@",zd,con,engine_cover)




        bumper=zd*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Consumables=con*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Rti=rti*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'Tata_Aig':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":round(bumper)})
                paid_passenger_cover_result[key].append({"Consumables":round(Consumables)})
                paid_passenger_cover_result[key].append({"Engine_Cover":round(Engine_Cover)})
                paid_passenger_cover_result[key].append({"Tyre_cover":round(Tyre_Cover)})
                paid_passenger_cover_result[key].append({"RTI":round(Rti)})
    else:
        zd=0/100
        con=0/100
        engine_cover=0/100
        tyre=0/100
        rti=0/100
        bumper=zd*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Consumables=con*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        Rti=rti*paid_passenger_cover_result['Tata_Aig'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'Tata_Aig':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":round(bumper)})
                paid_passenger_cover_result[key].append({"Consumables":round(Consumables)})
                paid_passenger_cover_result[key].append({"Engine_Cover":round(Engine_Cover)})
                paid_passenger_cover_result[key].append({"Tyre_cover":round(Tyre_Cover)})
                paid_passenger_cover_result[key].append({"RTI":round(Rti)})
    # if len(result_data_liberty) != 0:
    if result_data_liberty:
        # zd=result_liberty[0]['ZD']
        # con=result_liberty[0]['CON']
        # engine_cover=result_liberty[0]['ENGINE / EV']
        # tyre=result_liberty[0]['TYRE']
        # rti=result_liberty[0]['RTI']
        zd = result_data_liberty.zd
        con = result_data_liberty.con
        engine_cover = result_data_liberty.engine
        tyre = result_data_liberty.tyre
        rti = result_data_liberty.rti
        bumper=zd*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Consumables=con*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Rti=rti*paid_passenger_cover_result['liberty_gic'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'liberty_gic':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":round(bumper)})
                paid_passenger_cover_result[key].append({"Consumables":round(Consumables)})
                paid_passenger_cover_result[key].append({"Engine_Cover":round(Engine_Cover)})
                paid_passenger_cover_result[key].append({"Tyre_cover":round(Tyre_Cover)})
                paid_passenger_cover_result[key].append({"RTI":round(Rti)})

    else:
        zd=0/100
        con=0/100
        engine_cover=0/100
        tyre=0/100
        rti=0/100
        bumper=zd*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Consumables=con*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['liberty_gic'][0]['idv']
        Rti=rti*paid_passenger_cover_result['liberty_gic'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'liberty_gic':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":round(bumper)})
                paid_passenger_cover_result[key].append({"Consumables":round(Consumables)})
                paid_passenger_cover_result[key].append({"Engine_Cover":round(Engine_Cover)})
                paid_passenger_cover_result[key].append({"Tyre_cover":round(Tyre_Cover)})
                paid_passenger_cover_result[key].append({"RTI":round(Rti)})

    # if len(result_data_hdfc) != 0:
    if result_data_hdfc:
        # zd=result_hdfc[0]['ZD']
        # con=result_hdfc[0]['CON']
        # engine_cover=result_hdfc[0]['ENGINE']
        # tyre=result_hdfc[0]['TYRE'] 
        # rti=result_hdfc[0]['RTI']
        zd = result_data_hdfc.zd
        con = result_data_hdfc.con
        engine_cover = result_data_hdfc.engine
        tyre  = result_data_hdfc.tyre
        rti = result_data_hdfc.rti
        bumper=zd*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Consumables=con*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Rti=rti*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'hdfc_ergo':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":round(bumper)})
                paid_passenger_cover_result[key].append({"Consumables":round(Consumables)})
                paid_passenger_cover_result[key].append({"Engine_Cover":round(Engine_Cover)})
                paid_passenger_cover_result[key].append({"Tyre_cover":round(Tyre_Cover)})
                paid_passenger_cover_result[key].append({"RTI":round(Rti)})

    else:
        zd=0/100
        con=0/100
        engine_cover=0/100
        tyre=0/100
        rti=0/100
        bumper=zd*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Consumables=con*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        Rti=rti*paid_passenger_cover_result['hdfc_ergo'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'hdfc_ergo':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":round(bumper)})
                paid_passenger_cover_result[key].append({"Consumables":round(Consumables)})
                paid_passenger_cover_result[key].append({"Engine_Cover":round(Engine_Cover)})
                paid_passenger_cover_result[key].append({"Tyre_cover":round(Tyre_Cover)})
                paid_passenger_cover_result[key].append({"RTI":round(Rti)})

    # if len(result_data_icici) != 0:
    if result_data_icici:
        # zd=result_icici[0]['ZD']
        # con=result_icici[0]['CON']
        # engine_cover=result_icici[0]['ENGINE']
        # tyre=result_icici[0]['TYRE']
        # rti=result_icici[0]['RTI']
        zd = result_data_icici.zd
        con = result_data_icici.con
        engine_cover = result_data_icici.engine
        tyre = result_data_icici.tyre
        rti = result_data_icici.rti
        bumper=zd*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Consumables=con*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Rti=rti*paid_passenger_cover_result['icici_lombard'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'icici_lombard':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":round(bumper)})
                paid_passenger_cover_result[key].append({"Consumables":round(Consumables)})
                paid_passenger_cover_result[key].append({"Engine_Cover":round(Engine_Cover)})
                paid_passenger_cover_result[key].append({"Tyre_cover":round(Tyre_Cover)})
                paid_passenger_cover_result[key].append({"RTI":round(Rti)})

    else:
        zd=0/100
        con=0/100
        engine_cover=0/100
        tyre=0/100
        rti=0/100
        bumper=zd*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Consumables=con*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Engine_Cover=engine_cover*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Tyre_Cover=tyre*paid_passenger_cover_result['icici_lombard'][0]['idv']
        Rti=rti*paid_passenger_cover_result['icici_lombard'][0]['idv']
        for key in paid_passenger_cover_result.keys():
            if key == 'icici_lombard':
                paid_passenger_cover_result[key].append({"Bumper_to_Bumper":bumper})
                paid_passenger_cover_result[key].append({"Consumables":Consumables})
                paid_passenger_cover_result[key].append({"Engine_Cover":Engine_Cover})
                paid_passenger_cover_result[key].append({"Tyre_cover":Tyre_Cover})
                paid_passenger_cover_result[key].append({"RTI":Rti})
    return paid_passenger_cover_result


def rsa_cover(bumper):
    for key in bumper.keys():
        if key == 'Tata_Aig':
            bumper[key].append({"rsa_cover":272})
        elif key == 'liberty_gic':
            bumper[key].append({"rsa_cover":249})
        elif key == 'hdfc_ergo':
            bumper[key].append({"rsa_cover":350})
        elif key == 'icici_lombard':
            bumper[key].append({"rsa_cover":199})
    return bumper
def key_lock_cover(rsa_cover_result):
    for key in rsa_cover_result.keys():
        if key == 'Tata_Aig':
            rsa_cover_result[key].append({"key_lock_cover":315})
        elif key == 'liberty_gic':
            rsa_cover_result[key].append({"key_lock_cover":300})
        elif key == 'hdfc_ergo':
            rsa_cover_result[key].append({"key_lock_cover":499})
        elif key == 'icici_lombard':
            rsa_cover_result[key].append({"key_lock_cover":499})
    return rsa_cover_result
def loss_of_personal_belongings(key_lock_cover_result):
    for key in key_lock_cover_result.keys():
        if key == 'Tata_Aig':
            key_lock_cover_result[key].append({"loss_of_personal_belongings":135})
        elif key == 'liberty_gic':
            key_lock_cover_result[key].append({"loss_of_personal_belongings":250})
        elif key == 'hdfc_ergo':
            key_lock_cover_result[key].append({"loss_of_personal_belongings":199})
        elif key == 'icici_lombard':
            key_lock_cover_result[key].append({"loss_of_personal_belongings":500})
    return key_lock_cover_result
def net_premium(loss_of_personal_belongings):
    
    premium_amount_value_tata=loss_of_personal_belongings['Tata_Aig'][8]['premium_amount']
    third_party_premium_value_tata=loss_of_personal_belongings['Tata_Aig'][9]['third_party']
    owner_driver_cover_tata=loss_of_personal_belongings['Tata_Aig'][10]['driver_cover']
    paid_driver_cover_tata=loss_of_personal_belongings['Tata_Aig'][11]['paid_driver_cover']
    paid_passenger_cover_tata=loss_of_personal_belongings['Tata_Aig'][12]['paid_passenger_cover']
    rsa_cover_tata=loss_of_personal_belongings['Tata_Aig'][18]['rsa_cover']
    key_lock_cover_tata=loss_of_personal_belongings['Tata_Aig'][19]['key_lock_cover']
    loss_of_personal_belongings_value_tata=loss_of_personal_belongings['Tata_Aig'][20]['loss_of_personal_belongings']
    bumper_tata=loss_of_personal_belongings['Tata_Aig'][13]['Bumper_to_Bumper']
    Consumables_tata=loss_of_personal_belongings['Tata_Aig'][14]['Consumables']
    Engine_Cover_tata=loss_of_personal_belongings['Tata_Aig'][15]['Engine_Cover']
    Tyre_Cover_tata=loss_of_personal_belongings['Tata_Aig'][16]['Tyre_cover']
    Rti_tata=loss_of_personal_belongings['Tata_Aig'][17]['RTI']
    net_premium_value_tata=premium_amount_value_tata+third_party_premium_value_tata+owner_driver_cover_tata+paid_driver_cover_tata+paid_passenger_cover_tata+rsa_cover_tata+key_lock_cover_tata+loss_of_personal_belongings_value_tata+bumper_tata+Consumables_tata+Engine_Cover_tata+Tyre_Cover_tata+Rti_tata

    premium_amount_value_liberty=loss_of_personal_belongings['liberty_gic'][8]['premium_amount']
    third_party_premium_value_liberty=loss_of_personal_belongings['liberty_gic'][9]['third_party']
    owner_driver_cover_liberty=loss_of_personal_belongings['liberty_gic'][10]['driver_cover']
    paid_driver_cover_liberty=loss_of_personal_belongings['liberty_gic'][11]['paid_driver_cover']
    paid_passenger_cover_liberty=loss_of_personal_belongings['liberty_gic'][12]['paid_passenger_cover']
    rsa_cover_liberty=loss_of_personal_belongings['liberty_gic'][18]['rsa_cover']
    key_lock_cover_liberty=loss_of_personal_belongings['liberty_gic'][19]['key_lock_cover']
    loss_of_personal_belongings_value_liberty=loss_of_personal_belongings['liberty_gic'][20]['loss_of_personal_belongings']
    bumper_liberty=loss_of_personal_belongings['liberty_gic'][13]['Bumper_to_Bumper']
    Consumables_liberty=loss_of_personal_belongings['liberty_gic'][14]['Consumables']
    Engine_Cover_liberty=loss_of_personal_belongings['liberty_gic'][15]['Engine_Cover']
    Tyre_Cover_liberty=loss_of_personal_belongings['liberty_gic'][16]['Tyre_cover']
    Rti_liberty=loss_of_personal_belongings['liberty_gic'][17]['RTI']
    net_premium_value_liberty=premium_amount_value_liberty+third_party_premium_value_liberty+owner_driver_cover_liberty+paid_driver_cover_liberty+paid_passenger_cover_liberty+rsa_cover_liberty+key_lock_cover_liberty+loss_of_personal_belongings_value_liberty+bumper_liberty+Consumables_liberty+Engine_Cover_liberty+Tyre_Cover_liberty+Rti_liberty
    premium_amount_value_hdfc=loss_of_personal_belongings['hdfc_ergo'][8]['premium_amount']
    third_party_premium_value_hdfc=loss_of_personal_belongings['hdfc_ergo'][9]['third_party']
    owner_driver_cover_hdfc=loss_of_personal_belongings['hdfc_ergo'][10]['driver_cover']
    paid_driver_cover_hdfc=loss_of_personal_belongings['hdfc_ergo'][11]['paid_driver_cover']
    paid_passenger_cover_hdfc=loss_of_personal_belongings['hdfc_ergo'][12]['paid_passenger_cover']
    rsa_cover_hdfc=loss_of_personal_belongings['hdfc_ergo'][18]['rsa_cover']
    key_lock_cover_hdfc=loss_of_personal_belongings['hdfc_ergo'][19]['key_lock_cover']
    loss_of_personal_belongings_value_hdfc=loss_of_personal_belongings['hdfc_ergo'][20]['loss_of_personal_belongings']
    bumper_hdfc=loss_of_personal_belongings['hdfc_ergo'][13]['Bumper_to_Bumper']
    Consumables_hdfc=loss_of_personal_belongings['hdfc_ergo'][14]['Consumables']
    Engine_Cover_hdfc=loss_of_personal_belongings['hdfc_ergo'][15]['Engine_Cover']
    Tyre_Cover_hdfc=loss_of_personal_belongings['hdfc_ergo'][16]['Tyre_cover']
    Rti_hdfc=loss_of_personal_belongings['hdfc_ergo'][17]['RTI']
    net_premium_value_hdfc=premium_amount_value_hdfc+third_party_premium_value_hdfc+owner_driver_cover_hdfc+paid_driver_cover_hdfc+paid_passenger_cover_hdfc+rsa_cover_hdfc+key_lock_cover_hdfc+loss_of_personal_belongings_value_hdfc+bumper_hdfc+Consumables_hdfc+Engine_Cover_hdfc+Tyre_Cover_hdfc+Rti_hdfc
    premium_amount_value_icici=loss_of_personal_belongings['icici_lombard'][8]['premium_amount']
    third_party_premium_value_icici=loss_of_personal_belongings['icici_lombard'][9]['third_party']
    owner_driver_cover_icici=loss_of_personal_belongings['icici_lombard'][10]['driver_cover']
    paid_driver_cover_icici=loss_of_personal_belongings['icici_lombard'][11]['paid_driver_cover']
    paid_passenger_cover_icici=loss_of_personal_belongings['icici_lombard'][12]['paid_passenger_cover']
    rsa_cover_icici=loss_of_personal_belongings['icici_lombard'][18]['rsa_cover']
    key_lock_cover_icici=loss_of_personal_belongings['icici_lombard'][19]['key_lock_cover']
    loss_of_personal_belongings_value_icici=loss_of_personal_belongings['icici_lombard'][20]['loss_of_personal_belongings']
    bumper_icici=loss_of_personal_belongings['icici_lombard'][13]['Bumper_to_Bumper']
    Consumables_icici=loss_of_personal_belongings['icici_lombard'][14]['Consumables']
    Engine_Cover_icici=loss_of_personal_belongings['icici_lombard'][15]['Engine_Cover']
    Tyre_Cover_icici=loss_of_personal_belongings['icici_lombard'][16]['Tyre_cover']
    Rti_icici=loss_of_personal_belongings['icici_lombard'][17]['RTI']
    net_premium_value_icici=premium_amount_value_icici+third_party_premium_value_icici+owner_driver_cover_icici+paid_driver_cover_icici+paid_passenger_cover_icici+rsa_cover_icici+key_lock_cover_icici+loss_of_personal_belongings_value_icici+bumper_icici+Consumables_icici+Engine_Cover_icici+Tyre_Cover_icici+Rti_icici

    for keys in loss_of_personal_belongings.keys():
        if keys == 'Tata_Aig':
            loss_of_personal_belongings[keys].append({"net_premium":round(net_premium_value_tata)})
        elif keys == 'liberty_gic':
            loss_of_personal_belongings[keys].append({"net_premium":round(net_premium_value_liberty)})
        elif keys == 'hdfc_ergo':
            loss_of_personal_belongings[keys].append({"net_premium":round(net_premium_value_hdfc)})
        elif keys == 'icici_lombard':
            loss_of_personal_belongings[keys].append({"net_premium":round(net_premium_value_icici)})

    return loss_of_personal_belongings
def gst(premium_amount_value):
    premium_amount_value_tata=premium_amount_value['Tata_Aig'][21]['net_premium']
    gst_value_tata=premium_amount_value_tata*gst_rate/100 # Static value.
    premium_amount_value_liberty=premium_amount_value['liberty_gic'][21]['net_premium']
    gst_value_liberty=premium_amount_value_liberty*gst_rate/100 #Static value
    premium_amount_value_hdfc=premium_amount_value['hdfc_ergo'][21]['net_premium']
    gst_value_hdfc=premium_amount_value_hdfc*gst_rate/100 #Static value
    premium_amount_value_icici=premium_amount_value['icici_lombard'][21]['net_premium']
    gst_value_icici=premium_amount_value_icici*gst_rate/100 # static value

    for keys in premium_amount_value.keys():
        if keys == 'Tata_Aig':
            premium_amount_value[keys].append({"gst":round(gst_value_tata)})
        elif keys == 'liberty_gic':
            premium_amount_value[keys].append({"gst":round(gst_value_liberty)})
        elif keys == 'hdfc_ergo':
            premium_amount_value[keys].append({"gst":round(gst_value_hdfc)})
        elif keys == 'icici_lombard':
            premium_amount_value[keys].append({"gst":round(gst_value_icici)})
    return premium_amount_value

def total_premium(gst_value):
    net_premium_value_tata=gst_value['Tata_Aig'][21]['net_premium']
    gst_value_tata=gst_value['Tata_Aig'][22]['gst']
    net_premium_value_liberty=gst_value['liberty_gic'][21]['net_premium']
    gst_value_liberty=gst_value['liberty_gic'][22]['gst']
    net_premium_value_hdfc=gst_value['hdfc_ergo'][21]['net_premium']
    gst_value_hdfc=gst_value['hdfc_ergo'][22]['gst']
    net_premium_value_icici=gst_value['icici_lombard'][21]['net_premium']
    gst_value_icici=gst_value['icici_lombard'][22]['gst']
    total_premium_value_tata=net_premium_value_tata+gst_value_tata
    total_premium_value_liberty=net_premium_value_liberty+gst_value_liberty
    total_premium_value_hdfc=net_premium_value_hdfc+gst_value_hdfc
    total_premium_value_icici=net_premium_value_icici+gst_value_icici

    for keys in gst_value.keys():
        if keys == 'Tata_Aig':
            gst_value[keys].append({"total_premium":round(total_premium_value_tata)})
        elif keys == 'liberty_gic':
            gst_value[keys].append({"total_premium":round(total_premium_value_liberty)})
        elif keys == 'hdfc_ergo':
            gst_value[keys].append({"total_premium":round(total_premium_value_hdfc)})
        elif keys == 'icici_lombard':
            gst_value[keys].append({"total_premium":round(total_premium_value_icici)})
    return gst_value


def process_row_and_form_data(request):
    datadict = {'Tata_Aig':[],'liberty_gic':[],'hdfc_ergo':[],'icici_lombard':[]}
    data = json.loads(request.body)
    calculate_vehicle_age_result = calculate_vehicle_age(int(data.get('manufactureYear')))
    idv = calculate_idv(int(data.get('Ex-Showroom Price')), calculate_vehicle_age_result,datadict)
    total_od_premium = calculate_factor_rate(idv, calculate_vehicle_age_result, float(data.get('cc').split()[0]))

    ncb_rate=data.get('ncbRate')
    ncb_rate1 = ncb_rate_percentage(calculate_vehicle_age_result, ncb_rate,idv)
    print("NCB Rate:", ncb_rate1)
    ncb = ncb_calculation(calculate_vehicle_age_result,ncb_rate1)
    print("NCB:", ncb)
    after_ncb_result = after_ncb(ncb)
    print("After NCB:", after_ncb_result)
    discount_rate_percentage_tata = float(data.get('discountRatetata'))
    discount_rate_percentage_liberty = float(data.get('discountRateliberty'))
    discount_rate_percentage_hdfc = float(data.get('discountRatehdfc'))
    discount_rate_percentage_icici = float(data.get('discountRateicici'))
    discount_rate_amount_result = discount_rate_amount(after_ncb_result, discount_rate_percentage_tata,discount_rate_percentage_liberty,discount_rate_percentage_hdfc,discount_rate_percentage_icici)
    premium_amount_result = premium_amount(discount_rate_amount_result)
    print("Premium Amount:", premium_amount_result)
    third_party_premium_result = third_party_premium(calculate_vehicle_age_result, float(data.get('cc').split()[0]),premium_amount_result)
    owner_driver_cover_result = owner_driver_cover(calculate_vehicle_age_result,third_party_premium_result)
    print("Owner Driver Cover:", owner_driver_cover_result)
    paid_driver_cover_result = paid_driver_cover(calculate_vehicle_age_result,owner_driver_cover_result)
    print("Paid Driver Cover:", paid_driver_cover_result)
    paid_passenger_cover_result = paid_passenger_cover(paid_driver_cover_result)
    print("Paid Passenger Cover:", paid_passenger_cover_result)
    bumper=bumper_to_bumper(data.get('Brand Name'), data.get('Model Name'),paid_passenger_cover_result,int(data.get('manufactureYear')))
    print("Bumper to Bumper:", bumper)
    rsa_cover_result = rsa_cover(bumper)
    print("RSA Cover:", rsa_cover_result)
    key_lock_cover_result = key_lock_cover(rsa_cover_result)
    print("Key Lock Cover:", key_lock_cover_result)
    loss_of_personal_belongings_result = loss_of_personal_belongings(key_lock_cover_result)
    print("Loss of Personal Belongings:", loss_of_personal_belongings_result)
    net_premium_result = net_premium(loss_of_personal_belongings_result)
    print("Net Premium:", net_premium_result)
    gst_result = gst(premium_amount_result)
    print("GST:", gst_result)
    total_premium_result = total_premium(gst_result)
    print("Total Premium:", total_premium_result)
    header = ["Parameters"] + list(total_premium_result.keys())  
    nested_list = [header] 
    attributes = [list(item.keys())[0] for item in total_premium_result['Tata_Aig']]
    for attribute in attributes:
        row = [attribute]  
        for company, data_list in total_premium_result.items():
            value = next((item[attribute] for item in data_list if attribute in item), "")
            row.append(value)
        nested_list.append(row)
    print(nested_list)
    return JsonResponse({"data":nested_list})



def update_data1(data_dict):
    data_dict_updated = data_dict.keys()
    nested_keys = {company: list(data_dict[company].keys()) for company in data_dict}
    idv_tata =                              float(data_dict['Tata_Aig'].get('idv', 0))
    idv_liberty =                           float(data_dict['liberty_gic'].get('idv', 0))
    idv_hdfc =                              float(data_dict['hdfc_ergo'].get('idv', 0))
    idv_icici =                             float(data_dict['icici_lombard'].get('idv', 0))
    factor_rate_tata =                      float(data_dict['Tata_Aig'].get('rate', 0))
    factor_rate_liberty =                   float(data_dict['liberty_gic'].get('rate', 0))
    factor_rate_hdfc =                      float(data_dict['hdfc_ergo'].get('rate', 0))
    factor_rate_icici =                     float(data_dict['icici_lombard'].get('rate', 0))
    od_premium_tata =                       float(data_dict['Tata_Aig'].get('od_premium', 0))
    od_premium_liberty =                    float(data_dict['liberty_gic'].get('od_premium', 0))
    od_premium_hdfc =                       float(data_dict['hdfc_ergo'].get('od_premium', 0))
    od_premium_icici =                      float(data_dict['icici_lombard'].get('od_premium', 0))
    ncb_rate_tata =                         float(data_dict['Tata_Aig'].get('ncb_rate', 0))
    ncb_rate_liberty =                      float(data_dict['liberty_gic'].get('ncb_rate', 0))
    ncb_rate_hdfc =                         float(data_dict['hdfc_ergo'].get('ncb_rate', 0))
    ncb_rate_icici =                        float(data_dict['icici_lombard'].get('ncb_rate', 0))
    ncb_amount_tata =                       float(data_dict['Tata_Aig'].get('ncb', 0))
    ncb_amount_liberty =                    float(data_dict['liberty_gic'].get('ncb', 0))
    ncb_amount_hdfc =                       float(data_dict['hdfc_ergo'].get('ncb', 0))
    ncb_amount_icici =                      float(data_dict['icici_lombard'].get('ncb', 0))
    after_ncb_tata =                        float(data_dict['Tata_Aig'].get('after_ncb', 0))
    after_ncb_liberty =                     float(data_dict['liberty_gic'].get('after_ncb', 0))
    after_ncb_hdfc =                        float(data_dict['hdfc_ergo'].get('after_ncb', 0))
    after_ncb_icici =                       float(data_dict['icici_lombard'].get('after_ncb', 0))
    discount_rate_tata =                    float(data_dict['Tata_Aig'].get('discount_rate', 0))
    discount_rate_liberty =                 float(data_dict['liberty_gic'].get('discount_rate', 0))
    discount_rate_hdfc =                    float(data_dict['hdfc_ergo'].get('discount_rate', 0))
    discount_rate_icici =                   float(data_dict['icici_lombard'].get('discount_rate', 0))
    discount_rate_amount_tata =             float(data_dict['Tata_Aig'].get('discount_Amount', 0))
    discount_rate_amount_liberty =          float(data_dict['liberty_gic'].get('discount_Amount', 0))
    discount_rate_amount_hdfc =             float(data_dict['hdfc_ergo'].get('discount_Amount', 0))
    discount_rate_amount_icici =            float(data_dict['icici_lombard'].get('discount_Amount', 0))
    premium_amount_tata =                   float(data_dict['Tata_Aig'].get('premium_amount', 0))
    premium_amount_liberty =                float(data_dict['liberty_gic'].get('premium_amount', 0))
    premium_amount_hdfc =                   float(data_dict['hdfc_ergo'].get('premium_amount', 0))
    premium_amount_icici =                  float(data_dict['icici_lombard'].get('premium_amount', 0))
    third_party_premium_tata =              float(data_dict['Tata_Aig'].get('third_party', 0))
    third_party_premium_liberty =           float(data_dict['liberty_gic'].get('third_party', 0))
    third_party_premium_hdfc =              float(data_dict['hdfc_ergo'].get('third_party', 0))
    third_party_premium_icici =             float(data_dict['icici_lombard'].get('third_party', 0))
    owner_driver_cover_tata =               float(data_dict['Tata_Aig'].get('driver_cover', 0))
    owner_driver_cover_liberty =            float(data_dict['liberty_gic'].get('driver_cover', 0))
    owner_driver_cover_hdfc =               float(data_dict['hdfc_ergo'].get('driver_cover', 0))
    owner_driver_cover_icici =              float(data_dict['icici_lombard'].get('driver_cover', 0))
    paid_driver_cover_tata =                float(data_dict['Tata_Aig'].get('paid_driver_cover', 0))
    paid_driver_cover_liberty =             float(data_dict['liberty_gic'].get('paid_driver_cover', 0))
    paid_driver_cover_hdfc =                float(data_dict['hdfc_ergo'].get('paid_driver_cover', 0))
    paid_driver_cover_icici =               float(data_dict['icici_lombard'].get('paid_driver_cover', 0))
    paid_passenger_cover_tata =             float(data_dict['Tata_Aig'].get('paid_passenger_cover', 0))
    paid_passenger_cover_liberty =          float(data_dict['liberty_gic'].get('paid_passenger_cover', 0))
    paid_passenger_cover_hdfc =             float(data_dict['hdfc_ergo'].get('paid_passenger_cover', 0))
    paid_passenger_cover_icici =            float(data_dict['icici_lombard'].get('paid_passenger_cover', 0))
    bumper_tata =                           float(data_dict['Tata_Aig'].get('Bumper_to_Bumper', 0))
    bumper_liberty =                        float(data_dict['liberty_gic'].get('Bumper_to_Bumper', 0))
    bumper_hdfc =                           float(data_dict['hdfc_ergo'].get('Bumper_to_Bumper', 0))
    bumper_icici =                          float(data_dict['icici_lombard'].get('Bumper_to_Bumper', 0))
    Consumables_tata =                      float(data_dict['Tata_Aig'].get('Consumables', 0))
    Consumables_liberty =                   float(data_dict['liberty_gic'].get('Consumables', 0))
    Consumables_hdfc =                      float(data_dict['hdfc_ergo'].get('Consumables', 0))
    Consumables_icici =                     float(data_dict['icici_lombard'].get('Consumables', 0))
    Engine_Cover_tata =                     float(data_dict['Tata_Aig'].get('Engine_Cover', 0))
    Engine_Cover_liberty =                  float(data_dict['liberty_gic'].get('Engine_Cover', 0))
    Engine_Cover_hdfc =                     float(data_dict['hdfc_ergo'].get('Engine_Cover', 0))
    Engine_Cover_icici =                    float(data_dict['icici_lombard'].get('Engine_Cover', 0))
    Tyre_Cover_tata =                       float(data_dict['Tata_Aig'].get('Tyre_cover', 0))
    Tyre_Cover_liberty =                    float(data_dict['liberty_gic'].get('Tyre_cover', 0))
    Tyre_Cover_hdfc =                       float(data_dict['hdfc_ergo'].get('Tyre_cover', 0))
    Tyre_Cover_icici =                      float(data_dict['icici_lombard'].get('Tyre_cover', 0))
    Rti_tata =                              float(data_dict['Tata_Aig'].get('RTI', 0))
    Rti_liberty =                           float(data_dict['liberty_gic'].get('RTI', 0))
    Rti_hdfc =                              float(data_dict['hdfc_ergo'].get('RTI', 0))
    Rti_icici =                             float(data_dict['icici_lombard'].get('RTI', 0))
    rsa_cover_tata =                        float(data_dict['Tata_Aig'].get('rsa_cover', 0))
    rsa_cover_liberty =                     float(data_dict['liberty_gic'].get('rsa_cover', 0))
    rsa_cover_hdfc =                        float(data_dict['hdfc_ergo'].get('rsa_cover', 0))
    rsa_cover_icici =                       float(data_dict['icici_lombard'].get('rsa_cover', 0))
    key_lock_cover_tata =                   float(data_dict['Tata_Aig'].get('key_lock_cover', 0))
    key_lock_cover_liberty  =               float(data_dict['liberty_gic'].get('key_lock_cover', 0))
    key_lock_cover_hdfc =                   float(data_dict['hdfc_ergo'].get('key_lock_cover', 0))
    key_lock_cover_icici =                  float(data_dict['icici_lombard'].get('key_lock_cover', 0))
    loss_of_personal_belongings_tata =      float(data_dict['Tata_Aig'].get('loss_of_personal_belongings', 0))
    loss_of_personal_belongings_liberty =   float(data_dict['liberty_gic'].get('loss_of_personal_belongings', 0))
    loss_of_personal_belongings_hdfc =      float(data_dict['hdfc_ergo'].get('loss_of_personal_belongings', 0))
    loss_of_personal_belongings_icici =     float(data_dict['icici_lombard'].get('loss_of_personal_belongings', 0))
    net_premium_tata =                      float(data_dict['Tata_Aig'].get('net_premium', 0))
    net_premium_liberty =                   float(data_dict['liberty_gic'].get('net_premium', 0))
    net_premium_hdfc =                      float(data_dict['hdfc_ergo'].get('net_premium', 0))
    net_premium_icici =                     float(data_dict['icici_lombard'].get('net_premium', 0))
    gst_tata =                              float(data_dict['Tata_Aig'].get('gst', 0))
    gst_liberty =                           float(data_dict['liberty_gic'].get('gst', 0))
    gst_hdfc =                              float(data_dict['hdfc_ergo'].get('gst', 0))
    gst_icici =                             float(data_dict['icici_lombard'].get('gst', 0))
    total_premium_tata =                    float(data_dict['Tata_Aig'].get('total_premium', 0))
    total_premium_liberty=                  float(data_dict['liberty_gic'].get('total_premium', 0))
    total_premium_hdfc =                    float(data_dict['hdfc_ergo'].get('total_premium', 0))
    total_premium_icici =                   float(data_dict['icici_lombard'].get('total_premium', 0))
    od_premium_tata_value = round(idv_tata * factor_rate_tata / 100)
    od_premium_liberty_value = round(idv_liberty * factor_rate_liberty / 100)
    od_premium_hdfc_value = round(idv_hdfc * factor_rate_hdfc / 100)
    od_premium_icici_value = round(idv_icici * factor_rate_icici / 100)
    ncb_amount_tata_value = round(od_premium_tata_value * ncb_rate_tata / 100)
    ncb_amount_liberty_value = round(od_premium_liberty_value * ncb_rate_liberty / 100)
    ncb_amount_hdfc_value = round(od_premium_hdfc_value * ncb_rate_hdfc / 100)
    ncb_amount_icici_value = round(od_premium_icici_value * ncb_rate_icici / 100)
    after_ncb_tata_value = round(od_premium_tata_value - ncb_amount_tata_value)
    after_ncb_liberty_value = round(od_premium_liberty_value - ncb_amount_liberty_value)
    after_ncb_hdfc_value = round(od_premium_hdfc_value - ncb_amount_hdfc_value)
    after_ncb_icici_value = round(od_premium_icici_value - ncb_amount_icici_value)
    discount_rate_amount_tata_value = round(after_ncb_tata_value * discount_rate_tata / 100)
    discount_rate_amount_liberty_value = round(after_ncb_liberty_value * discount_rate_liberty / 100)
    discount_rate_amount_hdfc_value = round(after_ncb_hdfc_value * discount_rate_hdfc / 100)
    discount_rate_amount_icici_value = round(after_ncb_icici_value * discount_rate_icici / 100)
    premium_amount_tata_value = round(after_ncb_tata_value - discount_rate_amount_tata_value)
    premium_amount_liberty_value = round(after_ncb_liberty_value - discount_rate_amount_liberty_value)
    premium_amount_hdfc_value = round(after_ncb_hdfc_value - discount_rate_amount_hdfc_value)
    premium_amount_icici_value = round(after_ncb_icici_value - discount_rate_amount_icici_value)
    if premium_amount_tata == 0:
        premium_amount_tata_value = 0
    if premium_amount_liberty == 0:
        premium_amount_liberty_value = 0
    if premium_amount_hdfc == 0:
        premium_amount_hdfc_value = 0
    if premium_amount_icici == 0:
        premium_amount_icici_value = 0
    net_premium_tata_value = premium_amount_tata_value+third_party_premium_tata+owner_driver_cover_tata+paid_driver_cover_tata+paid_passenger_cover_tata+rsa_cover_tata+key_lock_cover_tata+loss_of_personal_belongings_tata+bumper_tata+Consumables_tata+Engine_Cover_tata+Tyre_Cover_tata+Rti_tata
    net_premium_liberty_value = premium_amount_liberty_value+third_party_premium_liberty+owner_driver_cover_liberty+paid_driver_cover_liberty+paid_passenger_cover_liberty+rsa_cover_liberty+key_lock_cover_liberty+loss_of_personal_belongings_liberty+bumper_liberty+Consumables_liberty+Engine_Cover_liberty+Tyre_Cover_liberty+Rti_liberty
    net_premium_hdfc_value = premium_amount_hdfc_value+third_party_premium_hdfc+owner_driver_cover_hdfc+paid_driver_cover_hdfc+paid_passenger_cover_hdfc+rsa_cover_hdfc+key_lock_cover_hdfc+loss_of_personal_belongings_hdfc+bumper_hdfc+Consumables_hdfc+Engine_Cover_hdfc+Tyre_Cover_hdfc+Rti_hdfc
    net_premium_icici_value = premium_amount_icici_value+third_party_premium_icici+owner_driver_cover_icici+paid_driver_cover_icici+paid_passenger_cover_icici+rsa_cover_icici+key_lock_cover_icici+loss_of_personal_belongings_icici+bumper_icici+Consumables_icici+Engine_Cover_icici+Tyre_Cover_icici+Rti_icici
    gst_tata_value = round(net_premium_tata_value * 18 / 100)
    gst_liberty_value = round(net_premium_liberty_value * 18 / 100)
    gst_hdfc_value = round(net_premium_hdfc_value * 18 / 100)
    gst_icici_value = round(net_premium_icici_value * 18 / 100)
    total_premium_tata_value = round(net_premium_tata_value + gst_tata_value)
    total_premium_liberty_value = round(net_premium_liberty_value + gst_liberty_value)
    total_premium_hdfc_value = round(net_premium_hdfc_value + gst_hdfc_value)
    total_premium_icici_value = round(net_premium_icici_value + gst_icici_value)
    data_dict_updated = {
        'Tata_Aig': {
            'idv': idv_tata,
            'rate': factor_rate_tata,
            'od_premium': od_premium_tata_value,
            'ncb_rate': ncb_rate_tata,
            'ncb': ncb_amount_tata_value,
            'after_ncb': after_ncb_tata_value,
            'discount_rate': discount_rate_tata,
            'discount_Amount': discount_rate_amount_tata_value,
            'premium_amount': premium_amount_tata_value,
            'third_party': third_party_premium_tata,
            'driver_cover': owner_driver_cover_tata,
            'paid_driver_cover': paid_driver_cover_tata,
            'paid_passenger_cover': paid_passenger_cover_tata,
            'Bumper_to_Bumper': bumper_tata,
            'Consumables': Consumables_tata,
            'Engine_Cover': Engine_Cover_tata,
            'Tyre_cover': Tyre_Cover_tata,
            'RTI': Rti_tata,
            'rsa_cover': rsa_cover_tata,
            'key_lock_cover': key_lock_cover_tata,
            'loss_of_personal_belongings': loss_of_personal_belongings_tata,
            'net_premium': net_premium_tata_value,
            'gst': gst_tata_value,
            'total_premium': total_premium_tata_value
        },
        'liberty_gic': {
            'idv': idv_liberty,
            'rate': factor_rate_liberty,
            'od_premium': od_premium_liberty_value,
            'ncb_rate': ncb_rate_liberty,
            'ncb': ncb_amount_liberty_value,
            'after_ncb': after_ncb_liberty_value,
            'discount_rate': discount_rate_liberty,
            'discount_Amount': discount_rate_amount_liberty_value,
            'premium_amount': premium_amount_liberty_value,
            'third_party': third_party_premium_liberty,
            'driver_cover': owner_driver_cover_liberty,
            'paid_driver_cover': paid_driver_cover_liberty,
            'paid_passenger_cover': paid_passenger_cover_liberty,
            'Bumper_to_Bumper': bumper_liberty,
            'Consumables': Consumables_liberty,
            'Engine_Cover': Engine_Cover_liberty,
            'Tyre_cover': Tyre_Cover_liberty,
            'RTI': Rti_liberty,
            'rsa_cover': rsa_cover_liberty,
            'key_lock_cover': key_lock_cover_liberty,
            'loss_of_personal_belongings': loss_of_personal_belongings_liberty,
            'net_premium': net_premium_liberty_value,
            'gst': gst_liberty_value,
            'total_premium': total_premium_liberty_value
        },
        'hdfc_ergo': {
            'idv': idv_hdfc,
            'rate': factor_rate_hdfc,
            'od_premium': od_premium_hdfc_value,
            'ncb_rate': ncb_rate_hdfc,
            'ncb': ncb_amount_hdfc_value,
            'after_ncb': after_ncb_hdfc_value,
            'discount_rate': discount_rate_hdfc,
            'discount_Amount': discount_rate_amount_hdfc_value,
            'premium_amount': premium_amount_hdfc_value,
            'third_party': third_party_premium_hdfc,
            'driver_cover': owner_driver_cover_hdfc,
            'paid_driver_cover': paid_driver_cover_hdfc,
            'paid_passenger_cover': paid_passenger_cover_hdfc,
            'Bumper_to_Bumper': bumper_hdfc,
            'Consumables': Consumables_hdfc,
            'Engine_Cover': Engine_Cover_hdfc,
            'Tyre_cover': Tyre_Cover_hdfc,
            'RTI': Rti_hdfc,
            'rsa_cover': rsa_cover_hdfc,
            'key_lock_cover': key_lock_cover_hdfc,
            'loss_of_personal_belongings': loss_of_personal_belongings_hdfc,
            'net_premium': net_premium_hdfc_value,
            'gst': gst_hdfc_value,
            'total_premium': total_premium_hdfc_value
        },
        'icici_lombard': {
            'idv': idv_icici,
            'rate': factor_rate_icici,
            'od_premium': od_premium_icici_value,
            'ncb_rate': ncb_rate_icici,
            'ncb': ncb_amount_icici_value,
            'after_ncb': after_ncb_icici_value,
            'discount_rate': discount_rate_icici,
            'discount_Amount': discount_rate_amount_icici_value,
            'premium_amount': premium_amount_icici_value,
            'third_party': third_party_premium_icici,
            'driver_cover': owner_driver_cover_icici,
            'paid_driver_cover': paid_driver_cover_icici,
            'paid_passenger_cover': paid_passenger_cover_icici,
            'Bumper_to_Bumper': bumper_icici,
            'Consumables': Consumables_icici,
            'Engine_Cover': Engine_Cover_icici,
            'Tyre_cover': Tyre_Cover_icici,
            'RTI': Rti_icici,
            'rsa_cover': rsa_cover_icici,
            'key_lock_cover': key_lock_cover_icici,
            'loss_of_personal_belongings': loss_of_personal_belongings_icici,
            'net_premium': net_premium_icici_value,
            'gst': gst_icici_value,
            'total_premium': total_premium_icici_value
        }
    }
    for company, company_data in data_dict_updated.items():
    # Get the valid keys for the current company from nested_keys
        valid_keys = nested_keys.get(company, [])
        
        # Remove keys from company data that are not in the valid keys
        data_dict_updated[company] = {key: value for key, value in company_data.items() if key in valid_keys}

    keys = list(data_dict_updated['Tata_Aig'].keys())

# Prepare the header row
    header = ['Parameters'] + list(data_dict_updated.keys())

    # Prepare the data rows
    data_rows = []
    for key in keys:
        row = [key] + [str(data_dict_updated[company][key]) for company in data_dict_updated]
        data_rows.append(row)

    # Combine the header and data rows into the final list
    final_data = [header] + data_rows

    print("data_dict_updated:", final_data)  
    return final_data 


def add_insurence(request):
    if request.method == 'POST':
        try:
            # Retrieve data from request.POST (FormData) or request.body (JSON)
            insurance_company = request.POST.get('insurance_company')
            name = request.POST.get('name')
            models = request.POST.get('models')
            zd = round(float(request.POST.get('zd', 0)) / 100, 4)
            con = round(float(request.POST.get('con', 0)) / 100, 4)
            engine = round(float(request.POST.get('engine', 0)) / 100, 4)
            tyre = round(float(request.POST.get('tyre', 0)) / 100, 4)
            rti = round(float(request.POST.get('rti', 0)) / 100, 4)
            year = request.POST.get('year')
            print(insurance_company, name, models, zd, con, engine, tyre, rti, year)
            new_user = Brand.objects.create(
                insurance_company=insurance_company,
                name=name,
                model=models,
                zd=zd,
                con=con,
                engine=engine,
                tyre=tyre,
                rti=rti,
                year=year
            )
            return JsonResponse({'success': True}, status=200)
        except:
            return JsonResponse({'success': False, 'message': "unsuccess"}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)


def update_table_data(request):
    try:
        updated_data = json.loads(request.body)
        updated_data = updated_data.get('updatedData')
        print('Received updated data:', updated_data)
        keys = updated_data[0][1:] 
        print("keys-----",keys) 
        data_dict = {key: {} for key in keys}  
        print("data_dict--------->",data_dict)
        for row in updated_data[1:]:
            parameter = row[0]  
            for i, value in enumerate(row[1:], start=0):
                company = keys[i]
                data_dict[company][parameter] = value
        final_data=update_data1(data_dict)
        print(final_data)
        return JsonResponse({"data":final_data})
    except Exception as e:
        # Handle any errors and return an error response
        print('Error:', e)
        return JsonResponse({'message': 'Error updating data. Please try again.'})


def show_data(request):
    search_query = request.GET.get('search', '').strip()  # Get search parameter
    page = request.GET.get('page', 1)  # Get page number, default to 1
    per_page = 15  # Number of items per page

    if search_query:
        
        brands = brands.filter(
            Q(name__icontains=search_query) |
            Q(insurance_company__icontains=search_query) |
            Q(models__icontains=search_query)
        )
    else:
        brands = Brand.objects.order_by('-id')
        paginator = Paginator(brands, per_page)
        page_obj = paginator.get_page(page)
        print(page_obj)
        print('brands data------->',brands)
    
    return render(request,'show_data.html', {"brands":page_obj, "search_query":search_query})





def update_data(request,id=None):
    if id is not None:
        brand = Brand.objects.get(id=id)
        return render(request,'update.html', {"brand":brand})
    else:
        if request.method == 'POST':
            id = request.POST.get('id')
            brand = Brand.objects.get(id=id)
            brand.insurance_company = request.POST.get('insurance_company')
            brand.name = request.POST.get('name')
            brand.model = request.POST.get('models')
            brand.zd = request.POST.get('zd')
            brand.con = request.POST.get('con')
            brand.engine = request.POST.get('engine')
            brand.tyre =   request.POST.get('tyre')
            brand.rti =    request.POST.get('rti')
            brand.save()
            return redirect('../../show-data')

def delete(request):
    id = request.POST.get('id')
    brand = Brand.objects.get(id=id)
    brand.delete()
    # flash('Brand deleted successfully!', 'danger')
    return redirect("../../show-data")