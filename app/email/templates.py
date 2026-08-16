from datetime import datetime


def order_confirmation_email(
    customer_name: str,
    order_id: int,
    order_date,
    payment_method: str,
    shipping_address: str,
    items: list,
    subtotal: float,
    shipping: float,
    grand_total: float
):

    rows = ""

    for item in items:

        rows += f"""
        <tr>
            <td style="padding:10px;border:1px solid #ddd;">
                {item["title"]}
            </td>

            <td style="padding:10px;border:1px solid #ddd;text-align:center;">
                {item["quantity"]}
            </td>

            <td style="padding:10px;border:1px solid #ddd;text-align:right;">
                ₹{item["price"]:.2f}
            </td>

            <td style="padding:10px;border:1px solid #ddd;text-align:right;">
                ₹{item["subtotal"]:.2f}
            </td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>Order Confirmation</title>

</head>

<body style="margin:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">

<table
width="100%"
cellpadding="0"
cellspacing="0"
style="background:#f4f6f8;padding:30px;">

<tr>

<td align="center">

<table
width="700"
style="
background:white;
border-radius:10px;
overflow:hidden;
">

<tr>

<td
style="
background:#0d6efd;
padding:25px;
color:white;
text-align:center;
">

<h1 style="margin:0;">
📚 BookStore
</h1>

<p style="margin-top:10px;">
Order Confirmation
</p>

</td>

</tr>

<tr>

<td style="padding:30px;">

<h2>

Hello {customer_name},

</h2>

<p>

Thank you for shopping with us.

Your order has been placed successfully.

</p>

<hr>

<h3>

Order Details

</h3>

<p>

<b>Order ID:</b>

#{order_id}

</p>

<p>

<b>Date:</b>

{order_date.strftime("%d-%m-%Y %I:%M %p")}

</p>

<p>

<b>Payment:</b>

{payment_method}

</p>

<table
width="100%"
cellpadding="0"
cellspacing="0"
style="border-collapse:collapse;margin-top:20px;">

<tr style="background:#f2f2f2;">

<th
style="padding:10px;border:1px solid #ddd;">

Book

</th>

<th
style="padding:10px;border:1px solid #ddd;">

Qty

</th>

<th
style="padding:10px;border:1px solid #ddd;">

Price

</th>

<th
style="padding:10px;border:1px solid #ddd;">

Subtotal

</th>

</tr>

{rows}

</table>

<br>

<table
align="right"
style="width:320px;">

<tr>

<td>

Subtotal

</td>

<td align="right">

₹{subtotal:.2f}

</td>

</tr>

<tr>

<td>

Shipping

</td>

<td align="right">

₹{shipping:.2f}

</td>

</tr>

<tr>

<td>

<b>Total</b>

</td>

<td align="right">

<b>

₹{grand_total:.2f}

</b>

</td>

</tr>

</table>

<div style="clear:both;"></div>

<br>

<h3>

Delivery Address

</h3>

<div
style="
background:#f8f9fa;
padding:15px;
border-radius:6px;
white-space:pre-line;
">

{shipping_address}

</div>

<br>

<p>

You can visit your account to track your order status.

</p>

<br>

<p>

Thank you for choosing

<b>

BookStore

</b>

❤️

</p>

</td>

</tr>

<tr>

<td
style="
background:#343a40;
color:white;
padding:18px;
text-align:center;
">

© 2026 BookStore

</td>

</tr>

</table>

</td>

</tr>

</table>

</body>

</html>
"""

    text = f"""
BookStore

Order Confirmation

Order ID : {order_id}

Customer : {customer_name}

Subtotal : ₹{subtotal:.2f}

Shipping : ₹{shipping:.2f}

Total : ₹{grand_total:.2f}

Payment : {payment_method}

Thank you for shopping with us.
"""

    return html, text
def order_status_email(
    customer_name: str,
    order_id: int,
    status: str,
    tracking_number: str | None = None,
    courier_name: str | None = None,
    estimated_delivery=None
):

    tracking_html = ""

    if tracking_number:

        tracking_html = f"""
        <p><b>Courier:</b> {courier_name}</p>
        <p><b>Tracking Number:</b> {tracking_number}</p>
        """

        if estimated_delivery:

            tracking_html += f"""
            <p>
            <b>Estimated Delivery:</b>
            {estimated_delivery.strftime("%d-%m-%Y")}
            </p>
            """

    html = f"""
    <html>

    <body style="font-family:Arial;background:#f5f5f5;padding:30px;">

        <div style="
            max-width:650px;
            margin:auto;
            background:white;
            border-radius:10px;
            padding:35px;
        ">

            <h1 style="color:#0d6efd;">
                📚 BookStore
            </h1>

            <h2>Hello {customer_name},</h2>

            <p>

            Your order

            <b>#{order_id}</b>

            has been updated.

            </p>

            <h2>

            Current Status

            </h2>

            <div style="
                background:#0d6efd;
                color:white;
                padding:15px;
                border-radius:8px;
                text-align:center;
                font-size:22px;
                font-weight:bold;
            ">

            {status}

            </div>

            <br>

            {tracking_html}

            <br>

            <p>

            You can login anytime to check your latest order status.

            </p>

            <br>

            <p>

            Thank you for shopping with BookStore ❤️

            </p>

        </div>

    </body>

    </html>
    """

    text = f"""

BookStore

Order #{order_id}

Status Updated

New Status : {status}

"""

    return html, text