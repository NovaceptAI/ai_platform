// import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
// import axios from "axios";

// const UserContext = createContext(null);
// export const useUser = () => useContext(UserContext);

// export function UserProvider({ children }) {
//   const [user, setUser] = useState(null);
//   const [loading, setLoading] = useState(true);

//   const fetchMe = useCallback(async () => {
//     try {
//       const token = localStorage.getItem("accessToken");
//       if (!token) { setUser(null); setLoading(false); return; }
//       const res = await axios.get("/api/users/me", {
//         headers: { Authorization: `Bearer ${token}` }
//       });
//       setUser(res.data);
//     } catch (e) {
//       console.error("/users/me error", e?.response?.data || e.message);
//       setUser(null);
//     } finally {
//       setLoading(false);
//     }
//   }, []);

//   useEffect(() => { fetchMe(); }, [fetchMe]);

//   const login = async (payload) => {
//     const res = await axios.post("/api/auth/login", payload);
//     localStorage.setItem("accessToken", res.data.access_token);
//     await fetchMe();
//     return res.data;
//   };

//   const signup = async (payload) => {
//     const res = await axios.post("/api/auth/signup", payload);
//     localStorage.setItem("accessToken", res.data.access_token);
//     await fetchMe();
//     return res.data;
//   };

//   const updateProfile = async (patch) => {
//     const token = localStorage.getItem("accessToken");
//     const res = await axios.put("/api/users/me", patch, { headers: { Authorization: `Bearer ${token}` } });
//     setUser(res.data);
//     return res.data;
//   };

//   const logout = () => {
//     localStorage.removeItem("accessToken");
//     setUser(null);
//   };

//   return (
//     <UserContext.Provider value={{ user, loading, login, signup, updateProfile, logout }}>
//       {children}
//     </UserContext.Provider>
//   );
// }