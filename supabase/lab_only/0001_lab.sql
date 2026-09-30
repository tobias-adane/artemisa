-- Solo para el proyecto de laboratorio (Fase 0). Nunca se aplica en producción.
-- El hash de LAB_BRIDGE_TOKEN lo escribe seed_demo.py en bridge_secrets.

-- Lectura con la clave anónima, solo para el usuario de laboratorio
create policy lab_read on users            for select to anon using (id = 'user_lab');
create policy lab_read on user_preferences for select to anon using (user_id = 'user_lab');
create policy lab_read on bridges          for select to anon using (user_id = 'user_lab');
create policy lab_read on spaces           for select to anon using (user_id = 'user_lab');
create policy lab_read on threads          for select to anon using (user_id = 'user_lab');
create policy lab_read on layers           for select to anon using (user_id = 'user_lab');
create policy lab_read on dispatches       for select to anon using (user_id = 'user_lab');
create policy lab_read on conversations    for select to anon using (user_id = 'user_lab');
create policy lab_read on messages         for select to anon using (user_id = 'user_lab');

-- El usuario de laboratorio, sus preferencias y su bridge
insert into users (id, first_name, locale, custom_instructions) values (
  'user_lab',
  'Alexander',
  'en',
  'Alexander and his partner both work 9 to 6 on weekdays.
Maya is 15. She leaves for school around 7:45 and gets home around 5.
Luna is our dog. She stays home and sleeps on the living room couch.
Packages usually come mid-morning in a white van.
Someone comes to clean on Tuesday mornings.
Tell me if anyone I don''t know comes to the door at night.'
);

insert into user_preferences (user_id) values ('user_lab');

insert into bridges (user_id) values ('user_lab');
