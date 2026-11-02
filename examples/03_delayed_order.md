# Delayed order with a wrong contact first

**Scenario:** get_order_status only with order number + contact; a wrong e-mail gets the same generic answer as a non-existent order; with the buyer's real e-mail (order 8, Ana Carolina) the order is shipped with tracking but its estimated delivery (2026-02-28) has passed, so the assistant apologizes and opens a ticket with handoff_to_human (the [demo] line).

- Model: `google_genai:gemini-3.5-flash-lite`
- Store clock: fixed at 2026-11-01 21:30 (America/Campo_Grande)
- Generated: 2026-11-02
- Command: `python -m emporio --script examples/scripts/03_delayed_order.txt --out examples/03_delayed_order.md`

---

### Turn 1

**Customer:** Hi, my order still hasn't arrived. Where is it?

_No tool call._

**Lia:**

> Hello! I'm Lia, the virtual assistant of Empório da Música. I'd be happy to help you check your order! 
> 
> To get started, could you please tell me your order number along with the e-mail or phone number used for the purchase?

---

### Turn 2

**Customer:** It's order 8, my email is ana.ferreira@gmail.com

- Tool call: `get_order_status({"contact": "ana.ferreira@gmail.com", "order_id": 8})`

**Lia:**

> I couldn't find an order with that number and e-mail. Could you double-check your order number and the e-mail or phone you used at checkout?

---

### Turn 3

**Customer:** Oh sorry, I used my other email: anacarol.ferreira@coldmail.com

- Tool call: `get_order_status({"order_id": 8, "contact": "anacarol.ferreira@coldmail.com"})`

**Lia:**

> Hi Ana! I found your order. 
> 
> Your order #8 for the Kala KA-C Concert Mogno was shipped, but unfortunately, it is currently delayed. The estimated delivery date was February 28, 2026. 
> 
> Here is your tracking code so you can follow it: **BRJL5544332BR**
> 
> I am so sorry for the delay! Would you like me to open a ticket with our support team to look into this for you?

---

### Turn 4

**Customer:** That's way too late. Yes, please open a ticket with the team.

- Tool call: `handoff_to_human({"order_id": 8, "summary": "Customer Ana Ferreira (order #8) is complaining about a delayed shipment (tracking BRJL5544332BR) past the estimated delivery of Feb 28, 2026. Wants assistance from the team.", "reason": "pedido_atrasado"})`

**Lia:**

> I've opened a ticket for our team regarding your delayed order. Your protocol number is **EMP-20261101-002**, and our team will reply within 24 business hours. 
> 
> Please note that our store is currently closed and reopens on Tuesday, November 3 at 09:00. 
> 
> Is there anything else I can help you with today?

`[demo] ticket EMP-20261101-002 saved to tickets.jsonl - stub, no real notification sent`

---

### Turn 5

**Customer:** Thank you.

_No tool call._

**Lia:**

> You're very welcome, Ana! If you need anything else once we're back open, just let us know. Have a great rest of your weekend! 😊
