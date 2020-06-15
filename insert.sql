INSERT INTO books (isbn, title, author, year) VALUES ('080213825X', 'Four Blondes', 'Candace Bushnell', 2000);

INSERT INTO users (username, password, email) VALUES ('admin', 'password', 'email@email.com');

INSERT INTO reviews (user_id, isbn, rating, review) VALUES (1, '380795272', 4,'test review');

select rating, review, username from reviews inner join users on reviews.user_id = users.id where isbn='380795272';