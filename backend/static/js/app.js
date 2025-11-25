let currentUserToken = null;
let editMovieId = null;

function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    firebase.auth().signInWithEmailAndPassword(email, password)
        .then(userCredential => {
            userCredential.user.getIdToken().then(token => {
                currentUserToken = token;
                fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({idToken: token})
                }).then(res => res.json()).then(data => {
                    if (data.success) {
                        document.getElementById("login-section").style.display = "none";
                        document.getElementById("movies-section").style.display = "block";
                        loadMovies();
                    } else {
                        alert("Error de login");
                    }
                });
            });
        })
        .catch(error => alert(error.message));
}

function logout() {
    fetch('/logout', {method: 'POST'})
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                firebase.auth().signOut();
                currentUserToken = null;
                document.getElementById("login-section").style.display = "block";
                document.getElementById("movies-section").style.display = "none";
            }
        });
}

function loadMovies() {
    fetch('/movies')
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById("movies-list");
            list.innerHTML = "";
            data.forEach(movie => {
                const li = document.createElement("li");
                li.innerHTML = `
                    <strong>${movie.title} (${movie.year})</strong> - ${movie.director} - ${movie.genre}
                    <button onclick="editMovie('${movie.id}', '${movie.title}', '${movie.year}', '${movie.director}', '${movie.genre}')">Editar</button>
                    <button onclick="deleteMovie('${movie.id}')">Eliminar</button>
                `;
                list.appendChild(li);
            });
        });
}

function addMovie() {
    const movie = {
        title: document.getElementById("title").value,
        year: document.getElementById("year").value,
        director: document.getElementById("director").value,
        genre: document.getElementById("genre").value
    };

    fetch('/movies', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(movie)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) loadMovies();
        else alert(data.error);
    });
}

function deleteMovie(id) {
    fetch(`/movies/${id}`, {method: 'DELETE'})
        .then(res => res.json())
        .then(data => {
            if (data.success) loadMovies();
            else alert(data.error);
        });
}

function editMovie(id, title, year, director, genre) {
    editMovieId = id;
    document.getElementById("edit-title").value = title;
    document.getElementById("edit-year").value = year;
    document.getElementById("edit-director").value = director;
    document.getElementById("edit-genre").value = genre;
    document.getElementById("edit-modal").style.display = "block";
    document.getElementById("overlay").style.display = "block";
}

function closeEdit() {
    document.getElementById("edit-modal").style.display = "none";
    document.getElementById("overlay").style.display = "none";
}


function saveEdit() {
    const movie = {
        title: document.getElementById("edit-title").value,
        year: document.getElementById("edit-year").value,
        director: document.getElementById("edit-director").value,
        genre: document.getElementById("edit-genre").value
    };

    fetch(`/movies/${editMovieId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(movie)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeEdit();
            loadMovies();
        } else alert(data.error);
    });
}
