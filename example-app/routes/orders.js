const express = require("express");
const { authenticateToken } = require("../middleware/auth");
const database = require("../data/database");

const router = express.Router();

// VULNERABLE: Get order by ID - No authorization check (IDOR)
// Exposes order details including shipping address to any authenticated user
router.get("/:id", authenticateToken, (req, res) => {
    const orderId = parseInt(req.params.id);
    const order = database.orders.find((o) => o.id === orderId);

    if (!order) {
        return res.status(404).json({ error: "Order not found" });
    }

    // VULNERABILITY: Returns order without checking if req.user.id === order.userId
    res.json(order);
});

// VULNERABLE: Update order - No authorization check (IDOR)
// Allows any user to modify any order (change status, shipping address, etc.)
router.put("/:id", authenticateToken, (req, res) => {
    const orderId = parseInt(req.params.id);
    const orderIndex = database.orders.findIndex((o) => o.id === orderId);

    if (orderIndex === -1) {
        return res.status(404).json({ error: "Order not found" });
    }

    // VULNERABILITY: No check if req.user.id === database.orders[orderIndex].userId
    const { status, shippingAddress } = req.body;

    if (status) {
        database.orders[orderIndex].status = status;
    }

    if (shippingAddress) {
        database.orders[orderIndex].shippingAddress = shippingAddress;
    }

    res.json({
        message: "Order updated successfully",
        order: database.orders[orderIndex],
    });
});

// VULNERABLE: Cancel/Delete order - No authorization check (IDOR)
router.delete("/:id", authenticateToken, (req, res) => {
    const orderId = parseInt(req.params.id);
    const orderIndex = database.orders.findIndex((o) => o.id === orderId);

    if (orderIndex === -1) {
        return res.status(404).json({ error: "Order not found" });
    }

    // VULNERABILITY: No check if req.user.id === database.orders[orderIndex].userId
    database.orders[orderIndex].status = "cancelled";

    res.json({
        message: "Order cancelled successfully",
        order: database.orders[orderIndex],
    });
});

module.exports = router;
