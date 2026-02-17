import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth';
import Layout from './Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Documents from './pages/Documents';
import Search from './pages/Search';
import ApiKeys from './pages/ApiKeys';
import Admin from './pages/Admin';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<Layout />}>
            <Route index element={<Documents />} />
            <Route path="/search" element={<Search />} />
            <Route path="/api-keys" element={<ApiKeys />} />
            <Route path="/admin" element={<Admin />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
