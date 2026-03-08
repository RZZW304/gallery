function openViewer(src){
    const viewer = document.getElementById("viewer");
    const img = document.getElementById("viewerImg");

    img.src = src;
    viewer.style.display = "flex";
}

function closeViewer(){
    document.getElementById("viewer").style.display = "none";
}