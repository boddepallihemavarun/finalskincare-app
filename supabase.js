import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm'

const SUPABASE_URL = "https://bfnqfxjtxdtyoprrqfki.supabase.co"
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmbnFmeGp0eGR0eW9wcnJxZmtpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMjE1MjAsImV4cCI6MjA4OTg5NzUyMH0.6tNMZ_2cgpzRxR-JaR0kk_8Pzrprrc4gGAzByQzIn8E"

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)