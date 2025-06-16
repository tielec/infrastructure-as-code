/**
 * Sample TypeScript module for testing documentation generation
 */
import { useState, useEffect } from 'react';
import axios from 'axios';

// Type definitions
export type UserID = string | number;
export type Coordinates = [number, number];
export type ApiResponse<T> = {
  data: T;
  status: number;
  message: string;
  timestamp: Date;
};

// Interface definitions
export interface User {
  id: UserID;
  username: string;
  email: string;
  isActive: boolean;
  role: UserRole;
  createdAt: Date;
}

export interface ApiConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
  retries?: number;
}

// Enum definition
export enum UserRole {
  Admin = 'ADMIN',
  Editor = 'EDITOR',
  Viewer = 'VIEWER',
  Guest = 'GUEST'
}

export enum HttpStatus {
  OK = 200,
  Created = 201,
  BadRequest = 400,
  Unauthorized = 401,
  Forbidden = 403,
  NotFound = 404,
  ServerError = 500
}

// Functions
export function formatDate(date: Date, format: string = 'yyyy-MM-dd'): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  let result = format;
  result = result.replace('yyyy', year.toString());
  result = result.replace('MM', month);
  result = result.replace('dd', day);
  
  return result;
}

export function calculateDistance(point1: Coordinates, point2: Coordinates): number {
  const [x1, y1] = point1;
  const [x2, y2] = point2;
  
  const deltaX = x2 - x1;
  const deltaY = y2 - y1;
  
  return Math.sqrt(deltaX * deltaX + deltaY * deltaY);
}

export async function fetchUserData(userId: UserID, config: ApiConfig): Promise<User> {
  try {
    const response = await axios.get(`${config.baseUrl}/users/${userId}`, {
      headers: config.headers,
      timeout: config.timeout || 5000
    });
    
    if (response.status === HttpStatus.OK) {
      return response.data as User;
    } else {
      throw new Error(`API request failed with status: ${response.status}`);
    }
  } catch (error) {
    console.error('Error fetching user data:', error);
    throw error;
  }
}

// Class definition
export class UserManager {
  private users: Map<UserID, User>;
  private apiConfig: ApiConfig;
  
  constructor(apiConfig: ApiConfig) {
    this.users = new Map<UserID, User>();
    this.apiConfig = apiConfig;
  }
  
  public async loadUser(userId: UserID): Promise<User> {
    // Check if user is already loaded
    if (this.users.has(userId)) {
      return this.users.get(userId)!;
    }
    
    // Fetch user from API
    const user = await fetchUserData(userId, this.apiConfig);
    this.users.set(userId, user);
    return user;
  }
  
  public getUser(userId: UserID): User | undefined {
    return this.users.get(userId);
  }
  
  public removeUser(userId: UserID): boolean {
    return this.users.delete(userId);
  }
  
  public get userCount(): number {
    return this.users.size;
  }
  
  public hasAdminUsers(): boolean {
    for (const user of this.users.values()) {
      if (user.role === UserRole.Admin) {
        return true;
      }
    }
    return false;
  }
}

// React Hook example
export function useUserData(userId: UserID, apiConfig: ApiConfig) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      try {
        setLoading(true);
        const userData = await fetchUserData(userId, apiConfig);
        
        if (isMounted) {
          setUser(userData);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err as Error);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    loadData();
    
    return () => {
      isMounted = false;
    };
  }, [userId, apiConfig]);
  
  return { user, loading, error };
}

// Utility functions and constants
export const DEFAULT_API_CONFIG: ApiConfig = {
  baseUrl: 'https://api.example.com/v1',
  timeout: 3000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  retries: 3
};

export function validateEmail(email: string): boolean {
  const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return regex.test(email);
}

export function generateRandomId(): UserID {
  return Math.random().toString(36).substring(2, 11);
}
