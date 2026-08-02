module.exports = (app) => {
    const notes = require('../controllers/note.controller.js');

    // Create a new Note
    app.post('/notes', notes.create);


    // Retrieve all Notes
    app.get('/notes/archived', notes.findArchived);

    app.get('/notes', notes.findAll);
    // Retrieve all Notes in a specific folder or category
    app.get('/notes/folder/:folder', notes.findByFolder);
    app.get('/notes/category/:category', notes.findByCategory);


    // Retrieve a single Note with noteId
    app.get('/notes/:noteId', notes.findOne);
    // Retrieve all Notes with a specific search query
    app.get('/notes/search/:query', notes.searchNotes);

    // Update a Note with noteId
    // Archive a Note with noteId
    app.put('/notes/:noteId/archive', notes.archive);
    app.put('/notes/:noteId', notes.update);

    // Delete a Note with noteId
    app.delete('/notes/:noteId', notes.delete);
}