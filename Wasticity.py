import wmi
import psutil
import taipy # Will be used for the front end side like a pop up application
import geocoder
import json
import platform
import subprocess
import time
import asyncio
import math
#Gets the location of the computer so that we can use the information
def UserLocation():
    location = geocoder.ip('me')
    state=location.state
    return state

#Gets the cost based on formula, but also will read through a large data set that is real time updated
def CostPerLocation(state):
    # Open and load the JSON file
    with open('electricity_rates.json', 'r',encoding='utf-8') as file:
     data = json.load(file)
    rate_lookup = {item['state']: item['rate'] for item in data['electricity_rates']}
    #Returns price per kw/hr from each state (not city specific)
    return rate_lookup.get(state,"")


#Reads the information given on your current status of Battery Percentages (will be tracked for later)
def BatteryInfo():
    battery=psutil.sensors.battery()
    batteryPercent=battery.percent
    isPowerPlugged=battery.power_plugged
    secondsTillCharged=battery.secsleft
    return batterPercent, isPowerPlugged, secondsTillCharged

#Gets type of computer that User is on
def get_computer_model():
    os_type = platform.system()
    
    try:
        if os_type == "Windows":
            model = subprocess.check_output("wmic csproduct get name", shell=True).decode().split("\n")[1].strip()
        elif os_type == "Darwin":  # macOS
            model = subprocess.check_output("sysctl -n hw.model", shell=True).decode().strip()
        elif os_type == "Linux":
            model = subprocess.check_output("cat /sys/devices/virtual/dmi/id/product_name", shell=True).decode().strip()
        else:
            model = "Unknown"
    except Exception as e:
        model = f"Could not determine model: {e}"

    return model

#Finds a name in the list of computers and if name not found we'll assume 100 Watts or 10 volts
def getVoltage(model):
    with open('Computers.json', 'r', encoding='utf-8') as file:
        companies = json.load(file)  # Load the entire list of companies
    
    # Loop through each company
    for company in companies:
        # Loop through the products within each company
        for product in company["products"]:
            # Check if the product name matches the model
            if product["name"].lower() in model.lower():
                return product["average_wattage"]
    
    # If the model is not found, return a default value
    return "100"  # Default value if the product isn't found

#-----------------------------------------
# Function to monitor the battery percentage
#Will need to change this where it updates the states from 1%
async def monitor_battery():
    previous_battery = psutil.sensors_battery().percent  # Initial battery percentage
    start_time = time.time()  # Start time to track duration
    print(f"Starting battery monitoring. Initial battery: {previous_battery}%")

    while True:
        current_battery = psutil.sensors_battery().percent  # Get current battery percentage

        if current_battery > previous_battery:  # Battery percentage has increased
            time_taken = time.time() - start_time  # Calculate time taken for the increase
            #Takes the time it took to go up 1%                                                 This may need to be improved
            return time_taken 
 
        await asyncio.sleep(5)  # Sleep for 60 seconds before checking again
    if time.time() - start_time >= 120:
            print("No increase in battery percentage for 120 seconds. Skipping to overflow check.")
            return None

def VoltageUsage(TimeTaken, ChargerWattage):
# Convert ChargerWattage to a float if it's not already
#Mathematically determine based on rate at which your battery goes up 1% and multiply by 100 to get a predicted time that way i can know the amount of voltage is used at 
    # estimate Use asynchio to get updates on battery and time it took
    #Model: Energy Added, Average Power Input, Estimate Voltage this voltage can be determined for CostToCharge
    #Believe this should determine how much volts you use based on computer model
    try:
        ChargerWattage = float(ChargerWattage)  # Convert to float
    except ValueError:
        print("Error: Charger wattage is not a valid number.")
        return None

    # If ChargerWattage is "100", it means the model is unknown, so we return early
    if ChargerWattage == 100:
        print("Charger wattage is unknown. Using default value.")
        return None

    # TimeTaken is in seconds, so we want to predict for one hour (3600 seconds)
    # Calculate how much energy is used in an hour, assuming linear charging speed
    # Predict the time for a 100% battery increase
    time_for_100_percent = TimeTaken * 100  # Time to fully charge the battery (in seconds)
    
    # Convert wattage to energy usage in one hour
    # Assuming the rate of battery increase is linear
    energy_used_in_one_hour = (ChargerWattage * 3600) / time_for_100_percent
    
    #TESTER print(f"Predicted energy used in 1 hour: {energy_used_in_one_hour:.2f} Wh (Watt-hours)")
    
    # Estimate the voltage: Power = Voltage x Current (We can assume current is constant)
    # Let's assume an average laptop current of 3A (this is a rough estimate, can be adjusted)

    current = 3  # Estimated current in amperes (this can vary based on the device)
    
    # Estimate voltage: Voltage = Power / Current
    estimated_voltage = energy_used_in_one_hour / current
    #TESTER print(f"Estimated voltage used in 1 hour: {estimated_voltage:.2f} V")
    
    return estimated_voltage

    
async def MaxChargeFinder():
    stuck_start_time = None  # To track when the battery starts being stuck
    prev_battery_percent = psutil.sensors_battery().percent  # Initial battery percentage
    max_charge_percentage = None  # This will hold the determined max charge percentage
    print("Monitoring for max charge...")

    while True:
        current_battery_percent = psutil.sensors_battery().percent  # Get current battery percentage

        # Check if battery has been stuck at the same percentage for the specified time
        if current_battery_percent == prev_battery_percent:
            if stuck_start_time is None:
                stuck_start_time = time.time()  # Start the stuck timer
        else:
            stuck_start_time = None  # Reset if battery percentage changes

        # If battery percentage has been stuck for the specified timeout, consider it max charge
        if stuck_start_time and (time.time() - stuck_start_time) >= 300:  # 5 minutes
            max_charge_percentage = current_battery_percent  # This becomes the max charge
            print(f"Battery stuck at {max_charge_percentage}% for more than 5 minutes.")
            break  # Exit the loop once we find the max charge

        prev_battery_percent = current_battery_percent
        await asyncio.sleep(30)  # Check every 30 seconds

    return max_charge_percentage

async def Overflow():
    max_charge_percentage = await MaxChargeFinder()  # Find the max charge percentage

    if max_charge_percentage is not None:
        stuck_start_time = time.time()  # Start the timer when max charge is found
        print(f"Max charge found at {max_charge_percentage}%. Monitoring overflow time...")

        while True:
            current_battery_percent = psutil.sensors_battery().percent  # Get current battery percentage
            if current_battery_percent == max_charge_percentage:
                # If battery is still at max charge, keep tracking how long it's been stuck
                time_stuck = time.time() - stuck_start_time
                print(f"Battery has been at {max_charge_percentage}% for {time_stuck / 60:.2f} minutes.")
            else:
                print(f"Battery is no longer at max charge. Exiting overflow monitoring.")
                break  # Exit if battery is no longer at max charge

            await asyncio.sleep(30)  # Check every 30 seconds


async def CostToCharge(model, state):
    #Cost = Energy kwH x Electricty Rate (kwh)
    #Energy=Power(W)xHours /1000 = kwh == Computer x Predicted hour usage /1000
    global time_stuck

    voltage=getVoltage(model)
    CostOfElectricPerHour= CostPerLocation(state)
    hours=time_stuck/3600

    #Returns cost specifically from the overflow in your region
    Cost= (voltage*(CostOfElectricPerHour*hours))/1000

    return Cost

#CHECK THIS FOR ERRORS WHEN TIME
async def main():
    # Run battery monitoring and use the result
    time_taken = await monitor_battery()

    if time_taken is None:
        # If monitor_battery returns None (no increase in 120 seconds), skip to MaxChargeFinder
        max_charge = await MaxChargeFinder()

        if max_charge is not None:
            # If max charge is found, use it in VoltageUsage
            model = get_computer_model()
            charger_wattage = getVoltage(model)
            VoltageUsage(time_taken, charger_wattage)
    else:
        print(f"Time taken for 1% increase: {time_taken:.2f} seconds")
        model = get_computer_model()
        charger_wattage = getVoltage(model)
        VoltageUsage(time_taken, charger_wattage)

    # Run the Overflow function to monitor how long the battery stays at max charge
    await Overflow()

asyncio.run(main())
##-----------------------------------------------------------------------------------------------
