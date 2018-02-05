import pandas as pd
import numpy as np

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

import requests
import schedule
import time
import sys

import matplotlib.pyplot as plt
#%matplotlib inline

# Import DBSCAN clustering libraries
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Test clusters will replace a fare in the fares list with a value we choose
def test_clusters(data_series, eps_val, swap_index, swap_value):
    data_series[swap_index] = swap_value
    ff = pd.DataFrame(data_series, columns=['fare']).reset_index()
    X = StandardScaler().fit_transform(ff)
    db = DBSCAN(eps=eps_val, min_samples=1).fit(X)

    labels = db.labels_
    clusters = len(set(labels))
    unique_labels = set(labels)
    colors = plt.cm.Spectral(np.linspace(0,
                            1, len(unique_labels)))

    plt.subplots(figsize=(12,8))

    for k, c in zip(unique_labels, colors):
        class_member_mask = (labels == k)
        xy = X[class_member_mask]
        plt.plot(xy[:, 0], xy[:, 1], 'o',
                 markerfacecolor=c,
                 markeredgecolor='k',
                 markersize=14)

    plt.title("Total Clusters: {}".format(clusters),
              fontsize=14, y=1.01)

def check_flights():
    # This is the url straight from the google.com/flights/explore search with the selected filters
    # From, To, Min-Max trip length
    url ="https://www.google.com/flights/explore/#explore;f=ORD,MDW;t=r-United+States-0x54eab584e432360b%253A0x1c3bb99243deb742;li=3;lx=7;d=2018-02-09"
    # Get the page using the headless PhantomJS browser
    driver = webdriver.PhantomJS()
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36")
    driver = webdriver.PhantomJS(desired_capabilities=dcap,service_args=['--ignore-ssl-errors=true'])
    driver.implicitly_wait(20)
    driver.get(url)

    # TODO: Fix the webdriverwait logic to wait until we've loaded the full page
    #wait = WebDriverWait(driver, 20)
    #wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,"div.CTPFVNB-l-c")))
    time.sleep(20)
    # Feed the page html source to BeautifulSoup
    s = BeautifulSoup(driver.page_source, "lxml")

    ### # This saves a screenshot of the page to "C:\Users\Lee"
    ### driver.save_screenshot(r'flight_explorer.png')

    # Collect all of the minimum prices listed on the search page
    # NOTE: This is the <div class="CTPFVNB-w-e"...> identifier associated with the 
    # minimum price.  The demo had a different tag, so this might change.
    best_price_tags = s.findAll('div', 'CTPFVNB-w-e')
    print(best_price_tags)

    if len(best_price_tags) < 4:
        print('Failed to Load Page Data')
        requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/dis0pGElU9md_Di5vDEDty',
            data={"value1": "script", "value2": "failed", "value3": ""})
        sys.exit(0)
    else:
        print('Successfully Loaded Page Data')

    best_prices = []
    for tag in best_price_tags:
        # .text returns the text inside the <div>text</div> section, which should be
        # $67 or some other price
        best_prices.append(int(tag.text.replace('$','').replace(',','')))

    ### # Debugging to list the best prices tags
    ### best_price_tags

    ### # Debugging to list the cheapest flight
    best_price = best_prices[0]
    ### best_price

    # Collect the heights of the shortest bar in each of the search graphs
    # This corresponds to the cheapest flight
    best_height_tags = s.findAll('div', 'CTPFVNB-w-f')
    best_heights = []
    for t in best_height_tags:
        # attrs is the list of html attributes, we select style=
        # Then we parse the text to find "height:" in the following format:
        # <div class=".." style="left:6px; height: 41.2116px;">
        best_heights.append(
            float(t.attrs['style'].split('height:')[1].replace('px;',''))
        )

    best_height = best_heights[0]
    ### best_height

    # Calculate the price per pixel of the best priced city
    # Note: this is only one city.  It would be better to do this for all the cities
    # This uses numpy to create an array, probably to make this easier as a next step
    pph = np.array(best_price)/np.array(best_height)
    ### pph

    # Get the bar heights for all flights in each city
    cities = s.findAll('div', 'CTPFVNB-w-o')
    ### cities

    # Parse the list of bars in the cheapest city and get the heights, then compute the fare
    # Note: This would have to change if we did ALL cities
    hlist=[]
    for bar in cities[0].findAll('div', 'CTPFVNB-w-x'):
        hlist.append(
            # We multiply * pph to get the actual fare, not just the height
            # fare = pph * height
            float(bar['style'].split('height: ')[1].replace('px;',''))*pph
        )

    # Calculate the fare for each bar: fare = height * pph
    # Using pandas (pd), which does statistics for us
    fares = pd.DataFrame(hlist, columns=['price'])
    ### fares
    ### fares.min()
    ### fares.median()
    ### fares.describe()

    # Density based spacial clustering of applications with noise, dbscan
    # Epsilon - determines distance 2 points can be from each other and still be in the same cluster
    # Min points - minimum number of points required to form a cluster

    # Use the pyplot package to draw a scatteplot of fares
    fig, ax = plt.subplots(figsize=(10,6))
    plt.scatter(np.arange(len(fares['price'])),fares['price'])

    # Set up code to identify and display the clusters
    px = [x for x in fares['price']]
    ff = pd.DataFrame(px, columns=['fare']).reset_index()

    X = StandardScaler().fit_transform(ff) # Subtract mean from each point and divide by std deviation
    db = DBSCAN(eps=.5, min_samples=1).fit(X) # Pass standardized data to DBSCAN, set eps and min_samples

    labels = db.labels_
    # Clusters labeled from 0 to n-1, set up colors
    clusters = len(set(labels))
    unique_labels = set(labels)
    # Generate color map of graph
    colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))

    plt.subplots(figsize=(12,8))
    for k, c in zip(unique_labels, colors):
        class_member_mask = (labels == k)
        xy = X[class_member_mask]
        plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=c,
            markeredgecolor='k', markersize=14)
    plt.title("Total Clusters: {}".format(clusters), fontsize=14,
        y=1.01)

    ### px[10]

    ### test_clusters(px, 1, 55, 50)

    # We expect the outlier to be the minimum price
    # Aggregate the data including the fare and the cluster associated with that fare
    pf = pd.concat([ff, pd.DataFrame(db.labels_,columns=['cluster'])], axis=1)
    ### pf

    # Display the cluster by min and count of the cluster
    rf = pf.groupby('cluster')['fare'].agg(['min','count'])
    print(rf)

    ### rf.describe([.10,.25,.5,.75,.9])

    #print("Clusters = " + clusters)

    # set up our rules
    # must have more than one cluster
    # cluster min must be equal to lowest price fare
    # cluster size must be less than 10th percentile
    # cluster must be $20 less than the next lowest price cluster
    if clusters > 1\
        and ff['fare'].min() == rf.iloc[0]['min']\
        and rf.iloc[0]['count'] < rf['count'].quantile(.10)\
        and rf.iloc[0]['fare'] + 100 < rf.iloc[1]['fare']:
            city = s.find('span', 'CTPFVNB-v-c').text
            fare = s.find('div', 'CTPFVNB-w-e').text
            requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/dis0pGElU9md_Di5vDEDty',
                data={"value1": city, "value2": fare, "value3": ""})
    else:
        print("no alert triggered")
        requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/dis0pGElU9md_Di5vDEDty',
            data={"value1": "None", "value2": "Triggered", "value3": ""})

    schedule.every(60).minutes.do(check_flights)

    while 1:
        schedule.run.pending()
        time.sleep(1)
        

# set up the scheduler to run our code every 60 minutes
print("HELLO")
check_flights()
#schedule.every(60).minutes.do(check_flights)
print("Goodbye")

