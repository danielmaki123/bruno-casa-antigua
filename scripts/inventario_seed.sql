BEGIN;

INSERT INTO proveedores (id, nombre, telefono, dia_pedido, notas, activo)
VALUES
    (1, 'Distribuidora Bebidas Locales', NULL, 'miercoles', 'Gaseosas, cervezas y hard seltzer locales', TRUE),
    (2, 'Casa de Licores y Vinos', NULL, 'lunes', 'Licores, rones y vinos importados y nacionales', TRUE),
    (3, 'Frutas y Concentrados del Valle', NULL, 'miercoles', 'Jugos naturales y concentrados', TRUE),
    (4, 'Postres Artesanales CA', NULL, 'lunes', 'Postres y reposteria', TRUE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO inventario_catalogo (producto, categoria, unidad_tipo, stock_minimo, proveedor_id, activo)
VALUES
    ('Toña', 'Gaseosas', 'unidades', 24.000, 1, TRUE),
    ('Victoria', 'Gaseosas', 'unidades', 24.000, 1, TRUE),
    ('Coca regular', 'Gaseosas', 'unidades', 36.000, 1, TRUE),
    ('Coca cero', 'Gaseosas', 'unidades', 24.000, 1, TRUE),
    ('Fanta naranja', 'Gaseosas', 'unidades', 18.000, 1, TRUE),
    ('Fanta roja', 'Gaseosas', 'unidades', 18.000, 1, TRUE),
    ('Fanta uva', 'Gaseosas', 'unidades', 12.000, 1, TRUE),
    ('Fresca', 'Gaseosas', 'unidades', 12.000, 1, TRUE),
    ('Canada Dry', 'Gaseosas', 'unidades', 12.000, 1, TRUE),
    ('Agua purificada', 'Gaseosas', 'unidades', 30.000, 1, TRUE),
    ('Agua gasificada limón Luna', 'Gaseosas', 'unidades', 12.000, 1, TRUE),
    ('Agua gasificada fresa Luna', 'Gaseosas', 'unidades', 12.000, 1, TRUE),

    ('Heineken', 'Cerveza', 'unidades', 18.000, 1, TRUE),
    ('Miller', 'Cerveza', 'unidades', 18.000, 1, TRUE),
    ('Sol', 'Cerveza', 'unidades', 18.000, 1, TRUE),
    ('Toña Lite', 'Cerveza', 'unidades', 24.000, 1, TRUE),
    ('Toña Ultra', 'Cerveza', 'unidades', 24.000, 1, TRUE),
    ('Victoria Frost', 'Cerveza', 'unidades', 18.000, 1, TRUE),
    ('Boreal', 'Cerveza', 'unidades', 12.000, 1, TRUE),
    ('Santiago Apóstol', 'Cerveza', 'unidades', 12.000, 1, TRUE),
    ('Guardabarranco', 'Cerveza', 'unidades', 12.000, 1, TRUE),
    ('Kaori', 'Cerveza', 'unidades', 12.000, 1, TRUE),

    ('Hard Limón', 'Hard Seltzer', 'unidades', 12.000, 1, TRUE),
    ('Hard Raspberry', 'Hard Seltzer', 'unidades', 12.000, 1, TRUE),
    ('Seltzer Grapefruit', 'Hard Seltzer', 'unidades', 12.000, 1, TRUE),
    ('Seltzer Sandia', 'Hard Seltzer', 'unidades', 12.000, 1, TRUE),
    ('Seltzer Trop Berry', 'Hard Seltzer', 'unidades', 12.000, 1, TRUE),

    ('Flor de Caña 12', 'Licores', 'botellas', 3.000, 2, TRUE),
    ('Flor de Caña 18', 'Licores', 'botellas', 2.000, 2, TRUE),
    ('Flor de Caña Gran Reserva', 'Licores', 'botellas', 3.000, 2, TRUE),
    ('Extra Lite litro', 'Licores', 'botellas', 4.000, 2, TRUE),
    ('Extra Lite 1/2', 'Licores', 'botellas', 6.000, 2, TRUE),
    ('José Cuervo', 'Licores', 'botellas', 3.000, 2, TRUE),
    ('Jarana', 'Licores', 'botellas', 3.000, 2, TRUE),
    ('Reposado', 'Licores', 'botellas', 2.000, 2, TRUE),
    ('Vodkalla', 'Licores', 'botellas', 3.000, 2, TRUE),
    ('Triple sec', 'Licores', 'botellas', 2.000, 2, TRUE),
    ('Vino tinto Tavernello', 'Vinos', 'botellas', 4.000, 2, TRUE),
    ('Undurraga', 'Vinos', 'botellas', 3.000, 2, TRUE),
    ('Viña Esmeralda', 'Vinos', 'botellas', 2.000, 2, TRUE),
    ('Aliwen', 'Vinos', 'botellas', 2.000, 2, TRUE),
    ('Luis Felipe', 'Vinos', 'botellas', 2.000, 2, TRUE),
    ('Espumoso rosé', 'Vinos', 'botellas', 2.000, 2, TRUE),
    ('Aperol', 'Licores', 'botellas', 2.000, 2, TRUE),
    ('Granadine', 'Licores', 'botellas', 2.000, 2, TRUE),

    ('Jugo de guayaba', 'Jugos', 'galones', 2.000, 3, TRUE),
    ('Jugo de naranja', 'Jugos', 'galones', 3.000, 3, TRUE),
    ('Jugo de limón', 'Jugos', 'galones', 2.000, 3, TRUE),
    ('Limonada clásica', 'Jugos', 'galones', 2.000, 3, TRUE),
    ('Limonada de fresa', 'Jugos', 'galones', 2.000, 3, TRUE),
    ('Té de limón', 'Jugos', 'galones', 2.000, 3, TRUE),
    ('Jamaica', 'Jugos', 'galones', 2.000, 3, TRUE),
    ('Toronja', 'Jugos', 'galones', 2.000, 3, TRUE),
    ('Concentrado de limón', 'Jugos', 'galones', 1.500, 3, TRUE),
    ('Concentrado de mango', 'Jugos', 'galones', 1.500, 3, TRUE),
    ('Concentrado de guayaba', 'Jugos', 'galones', 1.500, 3, TRUE),

    ('Flan', 'Postres', 'porciones', 8.000, 4, TRUE),
    ('Red velvet', 'Postres', 'porciones', 6.000, 4, TRUE),
    ('Torta alemana', 'Postres', 'porciones', 6.000, 4, TRUE),
    ('Pastel de zanahoria', 'Postres', 'porciones', 6.000, 4, TRUE),
    ('Cheesecake de limón', 'Postres', 'porciones', 6.000, 4, TRUE),
    ('Tres leches', 'Postres', 'porciones', 8.000, 4, TRUE)
ON CONFLICT (producto) DO NOTHING;

COMMIT;
