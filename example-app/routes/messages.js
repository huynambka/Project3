const express = require("express");
const { authenticateToken } = require("../middleware/auth");
const database = require("../data/database");

const router = express.Router();

// VULNERABLE: Get message by ID - No authorization check (IDOR)
// Any authenticated user can read any message
router.get("/:id", authenticateToken, (req, res) => {
    const messageId = parseInt(req.params.id);
    const message = database.messages.find((m) => m.id === messageId);

    if (!message) {
        return res.status(404).json({ error: "Message not found" });
    }

    // VULNERABILITY: Returns message without checking if user is sender or recipient
    // Should check: req.user.id === message.fromUserId || req.user.id === message.toUserId
    res.json(message);
});

// VULNERABLE: Delete message - No authorization check (IDOR)
// Any authenticated user can delete any message
router.delete("/:id", authenticateToken, (req, res) => {
    const messageId = parseInt(req.params.id);
    const messageIndex = database.messages.findIndex((m) => m.id === messageId);

    if (messageIndex === -1) {
        return res.status(404).json({ error: "Message not found" });
    }

    // VULNERABILITY: No check if user owns this message
    const deletedMessage = database.messages.splice(messageIndex, 1)[0];

    res.json({
        message: "Message deleted successfully",
        deletedMessage: {
            id: deletedMessage.id,
            subject: deletedMessage.subject,
        },
    });
});

// VULNERABLE: Mark message as read - No authorization check (IDOR)
router.patch("/:id/read", authenticateToken, (req, res) => {
    const messageId = parseInt(req.params.id);
    const messageIndex = database.messages.findIndex((m) => m.id === messageId);

    if (messageIndex === -1) {
        return res.status(404).json({ error: "Message not found" });
    }

    // VULNERABILITY: Should check if req.user.id === database.messages[messageIndex].toUserId
    database.messages[messageIndex].read = true;

    res.json({
        message: "Message marked as read",
        messageData: database.messages[messageIndex],
    });
});

module.exports = router;
