import csv

header = ['Product Name', 'Vendor Name', 'Product Title', 'Price', 'Currency', 'Bulk Discounts or Deals', 'Vendor Website', 'Short Product Description', 'Minimum Order Quantity', 'Shipping Time']
data = [
    # Office Chairs
    ['Office Chairs', 'IKEA Spain', 'MARKUS Office chair, Vissle dark grey, Medium', 159.00, 'EUR', '10% off for orders ≥ 5 units', 'https://www.ikea.com/es/en/p/markus-office-chair-vissle-dark-grey-70261150/', 'Ergonomic swivel chair, adjustable height, built-in lumbar support, mesh backrest.', 1, 'In-store pickup Same day; Delivery 2–6 days'],
    ['Office Chairs', 'IKEA Spain', 'FLINTAN Office chair with armrests, black', 99.99, 'EUR', '10% off for orders ≥ 5 units', 'https://www.ikea.com/es/en/p/flintan-office-chair-with-armrests-black-s89424468/', 'Simple ergonomic desk chair with padded seat and armrests, height adjustable via gas lift.', 1, 'In-store pickup Same day; Delivery 2–6 days'],
    ['Office Chairs', 'Officinca', 'Office chair STAY', 338.00, 'EUR', 'Special volume pricing for ≥ 10 units', 'https://officinca.es/en/ergonomic-chairs/958-office-chair-stay.html', 'Polypropylene frame, ergonomic upholstery, adjustable lumbar support, aluminum base with wheels.', 1, 'Free standard shipping (2–5 days)'],
    [],
    # MacBooks
    ['MacBooks', 'Apple Store Puerta del Sol', 'MacBook Air M2 (2022), 256 GB', 1349.00, 'EUR', '5% discount for educational/business bulk orders', 'https://www.apple.com/es/shop/buy-mac/macbook-air/13-inch', 'Lightweight laptop, M2 chip, 8-core CPU, 8-core GPU, 18 h battery life.', 1, 'In-store pickup Same day; Delivery 1–2 days'],
    ['MacBooks', 'Refurbed España', 'Refurbished MacBook Air M1, 256 GB', 879.00, 'EUR', '2–4 = –5%, ≥ 5 = –10%', 'https://www.refurbed.es/c/macbooks', 'Certified refurbished, M1 chip, up to 15 h battery, 12-month warranty.', 1, 'Free delivery 3–5 days'],
    ['MacBooks', 'K-Tuin', 'MacBook Pro M2, 14-inch, 512 GB', 1999.00, 'EUR', 'Ask for quote on orders ≥ 3 units', 'https://k-tuin.com/mac/macbook-pro-14-m2/', 'Pro performance with M2 Pro chip, Liquid Retina XDR.', 1, 'Delivery 1–3 days'],
    [],
    # Whiteboards
    ['Whiteboards', 'IKEA Spain', 'RELATERA Writing board + whiteboard (set of 2)', 20.00, 'EUR', '10% off for orders ≥ 5 sets', 'https://www.ikea.com/es/en/p/relatera-writing-board-whiteboard-set-of-2-light-grey-green-90558999', 'Includes angled writing board (28×9×33 cm) + whiteboard (37×9×37 cm).', 1, 'In-store pickup Same day; Delivery 2–6 days'],
    ['Whiteboards', 'FTC Visual', 'MagBoard® Basic (60×90 cm)', 165.00, 'EUR', '5% on orders ≥ 10; 10% on orders ≥ 20', 'https://ftcvisual.es/en/190-whiteboards-chalkboards', 'Steel whiteboard panel, wall mount, aluminum frame.', 1, '3–7 days'],
    ['Whiteboards', 'Amazon.es', 'Magnetic Whiteboard, Various colors (90×60 cm) + magnets', 60.95, 'EUR', '2–4 = –5%, 5+ = –12%', 'https://www.amazon.es/-/en/Magnetic-Whiteboard-Various-Colours-Turquoise/dp/B09VT9LXHW', 'Includes 10 magnets, wall hooks; melamine surface.', 1, '1–2 days Prime'],
]

# Writing to csv file
with open('data.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(header)
    for row in data:
        writer.writerow(row)