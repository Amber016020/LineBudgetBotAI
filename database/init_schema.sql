CREATE TABLE public.users (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  line_user_id text NOT NULL UNIQUE,
  display_name text,
  preferred_lang text DEFAULT 'zh-TW',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.categories (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id bigint REFERENCES public.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  parent_id bigint REFERENCES public.categories(id) ON DELETE SET NULL,
  is_system_default boolean DEFAULT false
);

CREATE TABLE public.transactions (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id bigint REFERENCES public.users(id) ON DELETE CASCADE,
  item text NOT NULL,
  amount numeric(12,2) NOT NULL,
  message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  type text CHECK (type IN ('expense', 'income')),
  category_id bigint REFERENCES public.categories(id) ON DELETE SET NULL
);
