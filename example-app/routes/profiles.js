const express = require("express");
const { authenticateToken } = require("../middleware/auth");
const database = require("../data/database");

const router = express.Router();

// VULNERABLE: Get profile by ID - No authorization check (IDOR)
// Returns sensitive PII data without verifying ownership
router.get("/:id", authenticateToken, (req, res) => {
    const profileId = parseInt(req.params.id);
    const profile = database.profiles.find((p) => p.id === profileId);

    if (!profile) {
        return res.status(404).json({ error: "Profile not found" });
    }

    // VULNERABILITY: Returns all sensitive data including SSN without ownership check
    // Should check if req.user.id === profile.userId
    res.json(profile);
});

// VULNERABLE: Update profile - No authorization check (IDOR)
// Any authenticated user can modify any profile
router.put("/:id", authenticateToken, (req, res) => {
    const profileId = parseInt(req.params.id);
    const profileIndex = database.profiles.findIndex((p) => p.id === profileId);

    if (profileIndex === -1) {
        return res.status(404).json({ error: "Profile not found" });
    }

    // VULNERABILITY: No check if req.user.id === database.profiles[profileIndex].userId
    const { firstName, lastName, phone, address, dateOfBirth, ssn } = req.body;

    if (firstName) database.profiles[profileIndex].firstName = firstName;
    if (lastName) database.profiles[profileIndex].lastName = lastName;
    if (phone) database.profiles[profileIndex].phone = phone;
    if (address) database.profiles[profileIndex].address = address;
    if (dateOfBirth) database.profiles[profileIndex].dateOfBirth = dateOfBirth;
    if (ssn) database.profiles[profileIndex].ssn = ssn;

    res.json({
        message: "Profile updated successfully",
        profile: database.profiles[profileIndex],
    });
});

// VULNERABLE: Get profile by user ID - predictable parameter
router.get("/user/:userId", authenticateToken, (req, res) => {
    const userId = parseInt(req.params.userId);
    const profile = database.profiles.find((p) => p.userId === userId);

    if (!profile) {
        return res.status(404).json({ error: "Profile not found" });
    }

    // VULNERABILITY: Should check if req.user.id === userId
    res.json(profile);
});

module.exports = router;
