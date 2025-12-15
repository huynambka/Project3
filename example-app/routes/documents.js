const express = require("express");
const { authenticateToken } = require("../middleware/auth");
const database = require("../data/database");

const router = express.Router();

// List user's own documents (properly protected)
router.get("/", authenticateToken, (req, res) => {
    const userDocuments = database.documents.filter((d) => d.userId === req.user.id);
    res.json({ documents: userDocuments });
});

// VULNERABLE: Get document by ID - No authorization check (IDOR)
router.get("/:id", authenticateToken, (req, res) => {
    const documentId = parseInt(req.params.id);
    const document = database.documents.find((d) => d.id === documentId);

    if (!document) {
        return res.status(404).json({ error: "Document not found" });
    }

    // VULNERABILITY: Returns document without checking if req.user.id === document.userId
    res.json(document);
});

// Create new document (properly protected)
router.post("/", authenticateToken, (req, res) => {
    const { title, content, type } = req.body;

    if (!title || !content) {
        return res.status(400).json({ error: "Title and content are required" });
    }

    const newDocument = {
        id: database.documents.length + 1,
        userId: req.user.id,
        title,
        content,
        type: type || "general",
        createdAt: new Date().toISOString(),
    };

    database.documents.push(newDocument);

    res.status(201).json({
        message: "Document created successfully",
        document: newDocument,
    });
});

// VULNERABLE: Update document - No authorization check (IDOR)
router.put("/:id", authenticateToken, (req, res) => {
    const documentId = parseInt(req.params.id);
    const documentIndex = database.documents.findIndex((d) => d.id === documentId);

    if (documentIndex === -1) {
        return res.status(404).json({ error: "Document not found" });
    }

    // VULNERABILITY: No check if req.user.id === database.documents[documentIndex].userId
    const { title, content, type } = req.body;

    if (title) database.documents[documentIndex].title = title;
    if (content) database.documents[documentIndex].content = content;
    if (type) database.documents[documentIndex].type = type;

    res.json({
        message: "Document updated successfully",
        document: database.documents[documentIndex],
    });
});

// VULNERABLE: Delete document - No authorization check (IDOR)
router.delete("/:id", authenticateToken, (req, res) => {
    const documentId = parseInt(req.params.id);
    const documentIndex = database.documents.findIndex((d) => d.id === documentId);

    if (documentIndex === -1) {
        return res.status(404).json({ error: "Document not found" });
    }

    // VULNERABILITY: No check if req.user.id === database.documents[documentIndex].userId
    const deletedDocument = database.documents.splice(documentIndex, 1)[0];

    res.json({
        message: "Document deleted successfully",
        document: {
            id: deletedDocument.id,
            title: deletedDocument.title,
        },
    });
});

module.exports = router;
