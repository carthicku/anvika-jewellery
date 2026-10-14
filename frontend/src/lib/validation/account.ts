/**
 * Form validation mirroring the backend rules (backend/app/core/security.py, schemas/account.py).
 * The backend validates again — these only give fast, friendly feedback.
 */
import { z } from 'zod';

export const INDIAN_STATES = [
  'Andaman and Nicobar Islands',
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chandigarh',
  'Chhattisgarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jammu and Kashmir',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Ladakh',
  'Lakshadweep',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Puducherry',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
] as const;

const MOBILE_RE = /^(?:\+?91)?[6-9]\d{9}$/;
export const isIndianMobile = (value: string) => MOBILE_RE.test(value.replace(/[\s\-()]/g, ''));

export const email = z.email('Enter a valid email address.');

export const newPassword = z
  .string()
  .min(10, 'Use at least 10 characters.')
  .max(128, 'Use at most 128 characters.')
  .refine((v) => !/^\d+$/.test(v), "Don't use only numbers.")
  .refine((v) => new Set(v).size >= 4, 'Use a less repetitive password.');

const optionalMobile = z
  .string()
  .trim()
  .refine((v) => v === '' || isIndianMobile(v), 'Enter a valid 10-digit Indian mobile number.');

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Enter your password.'),
});

export const registerSchema = z
  .object({
    full_name: z.string().trim().min(2, 'Please enter your name.').max(120),
    email,
    phone: optionalMobile,
    password: newPassword,
  })
  .refine((v) => v.password.toLowerCase() !== v.email.toLowerCase(), {
    path: ['password'],
    message: "Don't use your email address as your password.",
  });

export const resetSchema = z
  .object({ password: newPassword, confirm: z.string() })
  .refine((v) => v.password === v.confirm, {
    path: ['confirm'],
    message: 'Passwords do not match.',
  });

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Enter your current password.'),
    new_password: newPassword,
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, {
    path: ['confirm'],
    message: 'Passwords do not match.',
  });

export const profileSchema = z.object({
  full_name: z.string().trim().min(2, 'Please enter your name.').max(120),
  phone: optionalMobile,
});

export const addressSchema = z.object({
  label: z.string().trim().max(40),
  full_name: z.string().trim().min(2, 'Please enter the recipient’s name.').max(120),
  phone: z.string().trim().refine(isIndianMobile, 'Enter a valid 10-digit Indian mobile number.'),
  line1: z.string().trim().min(3, 'Please enter the house and street.').max(200),
  line2: z.string().trim().max(200),
  landmark: z.string().trim().max(120),
  city: z.string().trim().min(2, 'Please enter the city.').max(80),
  state: z.enum(INDIAN_STATES, { error: 'Choose a state or union territory.' }),
  pincode: z
    .string()
    .trim()
    .regex(/^[1-9][0-9]{5}$/, 'Enter a valid 6-digit PIN code.'),
  is_default_shipping: z.boolean(),
  is_default_billing: z.boolean(),
});

export type AddressFormValues = z.infer<typeof addressSchema>;
