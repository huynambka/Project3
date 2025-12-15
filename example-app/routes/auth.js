const express = require("express");
const jwt = require("jsonwebtoken");
const bcrypt = require("bcryptjs");
const database = require("../data/database");

const router = express.Router();

// Register new user
router.post("/register", async (req, res) => {
    try {
        const { username, email, password } = req.body;

        if (!username || !email || !password) {
            return res.status(400).json({ error: "All fields are required" });
        }

        // Check if user already exists
        const existingUser = database.users.find((u) => u.username === username || u.email === email);

        if (existingUser) {
            return res.status(409).json({ error: "Username or email already exists" });
        }

        // Create new user
        const hashedPassword = await bcrypt.hash(password, 10);
        const newUser = {
            id: database.users.length + 1,
            username,
            email,
            password: hashedPassword,
            role: "user",
            createdAt: new Date().toISOString(),
        };

        database.users.push(newUser);

        // Create profile for new user
        const newProfile = {
            id: database.profiles.length + 1,
            userId: newUser.id,
            firstName: "",
            lastName: "",
            phone: "",
            address: "",
            dateOfBirth: "",
            ssn: "",
        };
        database.profiles.push(newProfile);

        res.status(201).json({
            message: "User registered successfully",
            user: {
                id: newUser.id,
                username: newUser.username,
                email: newUser.email,
                role: newUser.role,
            },
        });
    } catch (error) {
        res.status(500).json({ error: "Registration failed" });
    }
});

// Login
router.post("/login", async (req, res) => {
    try {
        const { username, password } = req.body;

        if (!username || !password) {
            return res.status(400).json({ error: "Username and password are required" });
        }

        // Find user
        const user = database.users.find((u) => u.username === username);

        if (!user) {
            return res.status(401).json({ error: "Invalid credentials" });
        }

        // Verify password
        const validPassword = await bcrypt.compare(password, user.password);

        if (!validPassword) {
            return res.status(401).json({ error: "Invalid credentials" });
        }

        // Generate JWT token
        const token = jwt.sign({ id: user.id, username: user.username, role: user.role }, process.env.JWT_SECRET, {
            expiresIn: "24h",
        });

        res.json({
            message: "Login successful",
            token,
            user: {
                id: user.id,
                username: user.username,
                email: user.email,
                role: user.role,
            },
        });
    } catch (error) {
        res.status(500).json({ error: "Login failed" });
    }
});

module.exports = router;
