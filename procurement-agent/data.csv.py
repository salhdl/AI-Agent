import csv

data = [
    [
        "HP ZBook 14u G6",
        "Nmar.ma",
        "HP ZBook 14u G6",
        3400,
        "MAD",
        "Discounts up to 70% on select models",
        "https://nmar.ma/product/hp-zbook-14u-g6/",
        "Professional laptop, powerful and reliable for work and business use.",
        None,
        "Fast delivery in Morocco",
    ],
    [
        "HP EliteBook 845 G9",
        "Nmar.ma",
        "HP EliteBook 845 G9",
        6200,
        "MAD",
        "Seasonal discounts available",
        "https://nmar.ma/product/hp-elitebook-845-g9/",
        "High-performance professional laptop, suitable for demanding tasks.",
        None,
        "Fast delivery in Morocco",
    ],
    [
        "HP Victus 16-e1xxx",
        "Nmar.ma",
        "HP Victus 16-e1xxx",
        7500,
        "MAD",
        None,
        "https://nmar.ma/brand/hp/?add-to-cart=5346",
        "Gaming laptop with strong GPU, good for gamers and high-performance needs.",
        None,
        "Fast delivery in Morocco",
    ],
    [
        "Lenovo Legion 5",
        "Gamer Store Maroc",
        "Lenovo Legion 5",
        5800,
        "MAD",
        "Free delivery, 6 months warranty on new units",
        "https://gamerstoremaroc.com/product/lenovo-legion-5/",
        "Gaming laptop with solid performance and free delivery.",
        None,
        "Free delivery",
    ],
    [
        "MSI Pulse 16 AI C1VFKG",
        "Gamer Store Maroc",
        "MSI Pulse 16 AI C1VFKG",
        15800,
        "MAD",
        "Free delivery, 6 months warranty",
        "https://gamerstoremaroc.com/product/msi-pulse-16-ai-c1vfkg/",
        "High-end gaming laptop, suitable for demanding gaming and creative work.",
        None,
        "Free delivery",
    ],
    [
        "HP ProBook x360 435 G8",
        "Gamer Store Maroc",
        "HP ProBook x360 435 G8",
        3900,
        "MAD",
        "Free delivery, 6 months warranty",
        "https://gamerstoremaroc.com/product/hp-probook-x360-435-g8/",
        "Convertible professional laptop, good for business and flexible use.",
        None,
        "Free delivery",
    ],
    [
        "Lenovo Legion",
        "OpenSooq",
        "Lenovo Legion",
        5500,
        "MAD",
        "Negotiable prices and potential bulk deals",
        "https://ma.opensooq.com/en/marrakesh/computers-and-laptops/laptops",
        "Variety of laptops including Lenovo Legion, HP, and others; prices vary.",
        None,
        "Depends on seller",
    ],
]


with open('data.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Product Name', 'Vendor Name', 'Product Title', 'Price', 'Currency', 'Bulk Discounts or Deals', 'Vendor Website', 'Short Product Description', 'Minimum Order Quantity', 'Shipping Time']
    writer = csv.writer(csvfile)

    writer.writerow(fieldnames)

    for row in data:
        writer.writerow(row)
    
    # Add blank lines between products, though in this case each row is a unique product

print("CSV file 'data.csv' has been created.")