// Firebase Configuration for GuAn Platform
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getStorage, ref, uploadBytes, getDownloadURL, deleteObject } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-storage.js";

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBj9wQ04hnfPjowVvEa_yf8_Fq3VXVaH5I",
    authDomain: "giteksolhub-project.firebaseapp.com",
    projectId: "giteksolhub-project",
    storageBucket: "giteksolhub-project.firebasestorage.app",
    messagingSenderId: "917911843059",
    appId: "1:917911843059:web:0aa2438be6605d1f400786"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const storage = getStorage(app);

// Helper function to upload a photo to Firebase Storage
async function uploadPhotoToFirebase(file, userId, taloId, photoIndex) {
    return new Promise(async (resolve, reject) => {
        try {
            // Generate a unique filename
            const fileExt = file.name.split('.').pop();
            const fileName = `${userId}/${taloId}/${photoIndex}_${Date.now()}.${fileExt}`;
            const storageRef = ref(storage, `talos/${fileName}`);
            
            // Upload the file
            const snapshot = await uploadBytes(storageRef, file);
            
            // Get the download URL
            const downloadURL = await getDownloadURL(snapshot.ref);
            
            resolve({
                url: downloadURL,
                path: `talos/${fileName}`,
                type: file.type
            });
        } catch (error) {
            console.error('Error uploading to Firebase:', error);
            reject(error);
        }
    });
}

// Helper function to upload multiple photos
async function uploadMultiplePhotosToFirebase(files, userId, taloId) {
    const uploadPromises = [];
    for (let i = 0; i < files.length; i++) {
        if (files[i]) {
            uploadPromises.push(uploadPhotoToFirebase(files[i], userId, taloId, i));
        }
    }
    return Promise.all(uploadPromises);
}

// Helper function to delete a photo from Firebase Storage
async function deletePhotoFromFirebase(path) {
    try {
        const storageRef = ref(storage, path);
        await deleteObject(storageRef);
        return true;
    } catch (error) {
        console.error('Error deleting from Firebase:', error);
        return false;
    }
}

// Helper function to upload profile photo
async function uploadProfilePhotoToFirebase(file, userId) {
    return new Promise(async (resolve, reject) => {
        try {
            const fileExt = file.name.split('.').pop();
            const fileName = `profile_${Date.now()}.${fileExt}`;
            const storageRef = ref(storage, `profiles/${userId}/${fileName}`);
            
            const snapshot = await uploadBytes(storageRef, file);
            const downloadURL = await getDownloadURL(snapshot.ref);
            
            resolve({
                url: downloadURL,
                path: `profiles/${userId}/${fileName}`
            });
        } catch (error) {
            console.error('Error uploading profile photo:', error);
            reject(error);
        }
    });
}

// Export functions for use in other files
window.FirebaseStorage = {
    uploadPhotoToFirebase,
    uploadMultiplePhotosToFirebase,
    uploadProfilePhotoToFirebase,
    deletePhotoFromFirebase
};