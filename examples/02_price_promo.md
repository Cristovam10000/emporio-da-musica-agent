# Prices, promotions and installments

**Scenario:** find_product price with PIX, an inactive promotion answered with the current price (Takamine GD20 had a 12% "Oferta Especial" that is no longer active), an active promotion shown with original price and percent (Ohana CK-20, 20% off), PIX not stacking on promo prices, and the minimum installment rule (the promo price allows at most 5x, not 12x).

- Model: `google_genai:gemini-3.5-flash-lite`
- Store clock: fixed at 2026-11-01 21:30 (America/Campo_Grande)
- Generated: 2026-11-02
- Command: `python -m emporio --script examples/scripts/02_price_promo.txt --out examples/02_price_promo.md`

---

### Turn 1

**Customer:** How much is the Takamine GD20?

- Tool call: `find_product({"name": "Takamine GD20"})`

**Lia:**

> Hello! I'm Lia, the virtual assistant of Empório da Música. 🎵 
> 
> By the way, our store is currently closed, but I'm here to help! We'll reopen on Tuesday at 09:00.
> 
> The **Takamine GD20 Dreadnought Natural** is available for **R$ 2.199,00** (or **R$ 2.089,05** on PIX). You can also pay in up to **12x of R$ 183,25** interest-free! 
> 
> Would you like to know anything else about it?

---

### Turn 2

**Customer:** I saw a 12% offer on it some time ago, is it still on?

- Tool call: `find_product({"name": "Takamine GD20"})`

**Lia:**

> That promotion is not active at the moment. The current price is R$ 2.199,00 (or R$ 2.089,05 via PIX), and you can still pay in up to 12x of R$ 183,25 interest-free! 
> 
> Let me know if you need help with anything else.

---

### Turn 3

**Customer:** And the Ohana CK-20 ukulele?

- Tool call: `find_product({"name": "Ohana CK-20 ukulele"})`

**Lia:**

> The **Ohana CK-20 Concert Natural** is currently on promotion! 🎉 
> 
> It's going for **R$ 439,20** (20% off, was R$ 549,00). You can also pay in up to **5x of R$ 87,84** interest-free. 
> 
> *(Just a heads up: the 5% PIX discount doesn't apply since it's already on sale).* 
> 
> Would you like to know more about it or anything else?

---

### Turn 4

**Customer:** Can I stack the PIX discount on top of that?

- Tool call: `get_store_policy({"topic": "pagamento_parcelamento"})`

**Lia:**

> No, the 5% PIX discount doesn't apply to items that are already on sale. The promotional price of R$ 439,20 for the Ohana CK-20 is already our best offer for it! 
> 
> Can I help you with anything else today?

---

### Turn 5

**Customer:** Can I pay it in 12 installments?

_No tool call._

**Lia:**

> For the Ohana CK-20 Concert Natural, the maximum is up to 5x of R$ 87,84 interest-free. That's because our installment limits depend on the product's price and the minimum installment rules. 
> 
> Let me know if you'd like to go ahead with the 5 installments or if you have any other questions!
