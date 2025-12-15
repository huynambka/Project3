const express = require("express");
const { authenticateToken } = require("../middleware/auth");
const database = require("../data/database");

const router = express.Router();

// List all users (requires authentication)
router.get("/", authenticateToken, (req, res) => {
    const users = database.users.map((user) => ({
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt,
    }));

    res.json({ users });
});

// VULNERABLE: Get user by ID - No authorization check (IDOR)
// Any authenticated user can view any other user's details
router.get("/:id", authenticateToken, (req, res) => {
    const userId = parseInt(req.params.id);
    const user = database.users.find((u) => u.id === userId);

    if (!user) {
        return res.status(404).json({ error: "User not found" });
    }

    // VULNERABILITY: Returns sensitive data without checking if the requester owns this resource
    res.json({
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt,
    });
});

// VULNERABLE: Update user - No authorization check (IDOR)
// Any authenticated user can update any other user's information
router.put("/:id", authenticateToken, (req, res) => {
    const userId = parseInt(req.params.id);
    const userIndex = database.users.findIndex((u) => u.id === userId);

    if (userIndex === -1) {
        return res.status(404).json({ error: "User not found" });
    }

    // VULNERABILITY: No check if req.user.id === userId
    const { email, role } = req.body;

    if (email) {
        database.users[userIndex].email = email;
    }

    // Even more dangerous - allows privilege escalation
    if (role) {
        database.users[userIndex].role = role;
    }

    res.json({
        message: "User updated successfully",
        user: {
            id: database.users[userIndex].id,
            username: database.users[userIndex].username,
            email: database.users[userIndex].email,
            role: database.users[userIndex].role,
        },
    });
});

// VULNERABLE: Delete user - No authorization check (IDOR)
// Any authenticated user can delete any other user
router.delete("/:id", authenticateToken, (req, res) => {
    const userId = parseInt(req.params.id);
    const userIndex = database.users.findIndex((u) => u.id === userId);

    if (userIndex === -1) {
        return res.status(404).json({ error: "User not found" });
    }

    // VULNERABILITY: No check if req.user.id === userId or if user is admin
    const deletedUser = database.users.splice(userIndex, 1)[0];

    res.json({
        message: "User deleted successfully",
        user: {
            id: deletedUser.id,
            username: deletedUser.username,
        },
    });
});

module.exports = router;
