const Note = require('../models/note.model.js');

// Create and Save a new Note
exports.create = (req, res) => {
    // Validate request
    if (!req.body.content) {
        return res.status(400).send({
            message: "Note content can not be empty"
        });
    }

    // Create a Note
    const note = new Note({
        isArchived: false,
        title: req.body.title || "Untitled Note",
        content: req.body.content,
        tags: req.body.tags || [],
        folder: req.body.folder || "Uncategorized",
        subcategory: req.body.subcategory || "Uncategorized",
        priority: req.body.priority || "Low"
    });

    // Save Note in the database
    note.save()
        .then(data => {
            res.send(data);
        }).catch(err => {
            res.status(500).send({
                message: err.message || "Some error occurred while creating the Note."
            });
        });
};

// Retrieve and return all notes from the database.
exports.findAll = (req, res) => {
    let query = {};
    if (req.query.tag) {
        query.tags = req.query.tag;
    }
    if (req.query.folder) {
        query.folder = req.query.folder;
    }
    if (req.query.subcategory) {
        query.subcategory = req.query.subcategory;
    }
    if (req.query.priority) {
        query.priority = req.query.priority;
    }
    if (req.query.search) {
        query.$or = [
            { title: { $regex: req.query.search, $options: 'i' } },
            { content: { $regex: req.query.search, $options: 'i' } }
        ];
    }

    Note.find(query)
        .then(notes => {
            res.send(notes);
        }).catch(err => {
            res.status(500).send({
                message: err.message || "Some error occurred while retrieving notes."
            });
        });
};

// Find a single note with a noteId
exports.findOne = (req, res) => {
    Note.findById(req.params.noteId)
        .then(note => {
            if (!note) {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            res.send(note);
        }).catch(err => {
            if (err.kind === 'ObjectId') {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            return res.status(500).send({
                message: "Error retrieving note with id " + req.params.noteId
            });
        });
};

// Update a note identified by the noteId in the request
exports.update = (req, res) => {
    // Validate Request
    if (!req.body.content) {
        return res.status(400).send({
            message: "Note content can not be empty"
        });
    }

    // Find note and update it with the request body
    Note.findByIdAndUpdate(req.params.noteId, {
        isArchived: req.body.isArchived || false,
        title: req.body.title || "Untitled Note",
        content: req.body.content,
        tags: req.body.tags || [],
        folder: req.body.folder || "Uncategorized",
        subcategory: req.body.subcategory || "Uncategorized",
        priority: req.body.priority || "Low"
    }, { new: true })
        .then(note => {
            if (!note) {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            res.send(note);
        }).catch(err => {
            if (err.kind === 'ObjectId') {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            return res.status(500).send({
                message: "Error updating note with id " + req.params.noteId
            });
        });
};

exports.archive = (req, res) => {
    Note.findByIdAndUpdate(req.params.noteId, { isArchived: true }, { new: true })
        .then(note => {
            if (!note) {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            res.send(note);
        }).catch(err => {
            if (err.kind === 'ObjectId') {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            return res.status(500).send({
                message: "Error archiving note with id " + req.params.noteId
            });
        });
}

exports.delete = (req, res) => {
    Note.findByIdAndDelete(req.params.noteId)
        .then(note => {
            if (!note) {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            res.send({ message: "Note deleted successfully!" });
        }).catch(err => {
            if (err.kind === 'ObjectId' || err.name === 'NotFound') {
                return res.status(404).send({
                    message: "Note not found with id " + req.params.noteId
                });
            }
            return res.status(500).send({
                message: "Could not delete note with id " + req.params.noteId
            });
        });
};

// Retrieve notes by folder
exports.findByFolder = (req, res) => {
    Note.find({ folder: req.params.folder })
        .then(notes => {
            res.send(notes);
        }).catch(err => {
            res.status(500).send({
                message: err.message || "Some error occurred while retrieving notes by folder."
            });
        });
};

// Retrieve notes by category
exports.findByCategory = (req, res) => {
    Note.find({ categories: req.params.category })
        .then(notes => {
            res.send(notes);
        }).catch(err => {
            res.status(500).send({
                message: err.message || "Some error occurred while retrieving notes by category."
            });
        });
};

exports.findArchived = (req, res) => {
    Note.find({ isArchived: true })
        .then(notes => {
            res.send(notes);
        }).catch(err => {
            res.status(500).send({
                message: err.message || "Some error occurred while retrieving archived notes."
            });
        });
}

exports.searchNotes = (req, res) => {
    const query = req.params.query;
    Note.find({
        $or: [
            { title: { $regex: query, $options: 'i' } },
            { content: { $regex: query, $options: 'i' } }
        ]
    })
        .then(notes => {
            res.send(notes);
        }).catch(err => {
            res.status(500).send({
                message: err.message || "Some error occurred while searching notes."
            });
        });
};
