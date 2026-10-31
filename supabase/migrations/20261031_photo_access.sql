begin;
-- Keep photo authorization in one fresh-snapshot check on each Storage SELECT.
create or replace function dating.can_read_photo(object_path text) returns boolean
language sql volatile security definer set search_path='' as $$
 select auth.uid() is not null and exists(select 1 from dating.photos p
 where p.path=object_path and(p.user_id=auth.uid()or not exists(select 1 from dating.blocks b
 where(b.blocker=auth.uid()and b.blocked=p.user_id)or(b.blocked=auth.uid()and b.blocker=p.user_id))));
$$;
revoke all on function dating.can_read_photo(text) from public,anon;
grant execute on function dating.can_read_photo(text)to authenticated;
drop policy if exists dating_storage_read on storage.objects;
create policy dating_storage_read on storage.objects for select to authenticated
 using(bucket_id='dating-photos'and dating.can_read_photo(name));
commit;
