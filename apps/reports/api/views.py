from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    UpdateAPIView,
    DestroyAPIView,
    RetrieveAPIView
)
from rest_framework.permissions import (
    IsAuthenticated, AllowAny
)
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from ..models import ReportType, Report, ReportFile
from .serializers import (
    ReportTypeSerializer,
    ReportSerializer,
    ReportCreateSerializer,
    ReportFilesSerializer,
)


class ReportTypeListAPIView(ListAPIView):
    """
    ReportType API to Retrieve
    """
    serializer_class = ReportTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReportType.objects.all()

    def list(self, request, *args, **kwargs):
        serializer = self.serializer_class(self.get_queryset(), many=True)
        data = {"report_types": serializer.data}
        return Response(data, status=HTTP_200_OK)


class ReportCreateAPIView(CreateAPIView):
    """
    API to create Report
    """
    serializer_class = ReportCreateSerializer
    permission_classes = [IsAuthenticated]
    queryset = Report.objects.all()

    def post(self, request, *args, **kwargs):
        serializer = ReportCreateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            report_obj = serializer.save(user=request.user)
            data = ReportSerializer(report_obj).data
            return Response(data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ReportUpdateAPIView(UpdateAPIView):
    """
    API to update Report
    """
    serializer_class = ReportCreateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    queryset = Report.objects.all()

    def partial_update(self, request, *args, **kwargs):
        serializer = ReportCreateSerializer(data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            report_obj = serializer.update(instance=self.get_object(), validated_data=request.data)
            data = ReportSerializer(report_obj).data
            return Response(data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ReportRetrieveAPIView(RetrieveAPIView):
    """
    API to Retrieve Report
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    queryset = Report.objects.all()

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = ReportSerializer(obj)
        data = serializer.data
        file_objs = ReportFile.objects.filter(file_report=obj)
        files = []
        for file_obj in file_objs:
            file = {}
            file['file'] = file_obj.file.url
            files.append(file)
        data['files'] = files
        return Response(data, status=HTTP_200_OK)


class ReportDeleteAPIView(DestroyAPIView):
    """
    API to delete Report
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Report.objects.all()


class ReportFileUploadAPIView(CreateAPIView):
    serializer_class = ReportFilesSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ReportFilesSerializer(data=request.data)
        status = {}

        if serializer.is_valid(raise_exception=True):
            status["status"] = "No files"
            video1 = request.FILES.get('video1', None)
            video2 = request.FILES.get('video2', None)
            image1 = request.FILES.get('image1', None)
            image2 = request.FILES.get('image2', None)
            image3 = request.FILES.get('image3', None)
            image4 = request.FILES.get('image4', None)
            report_id = request.data.get('file_report', None)
            report_obj = Report.objects.get(id=report_id)
            if image1:
                status = self.imageupload(status, image1, report_obj, "image1")
            if image2:
                status = self.imageupload(status, image2, report_obj, "image2")
            if image3:
                status = self.imageupload(status, image3, report_obj, "image3")
            if image4:
                status = self.imageupload(status, image4, report_obj, "image4")
            if video1:
                status = self.uploadvideo(status, video1, report_obj, "video1")
            if video2:
                status = self.uploadvideo(status, video2, report_obj, "video2")
            return Response(status, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def imageupload(self, status, image, report_obj, name):
        file_names = self.get_file_names(report_obj)
        if image.name not in file_names:
            try:
                ReportFile.objects.create(file=image, file_report=report_obj)
                status[name] = name + " has been uploaded"
            except:
                status[name] = "Error occurred while uploading"
        else:
            status[name] = name + " file already exists"
        if "status" in status:
            status.pop("status")
        return status

    def uploadvideo(self, status, video, report_obj, name):
        file_names = self.get_file_names(report_obj)
        if video.name not in file_names:
            if video.size > 20971520:
                status[name] = "video size greater then 20MB"
            else:
                ReportFile.objects.create(file=video, file_report=report_obj)
                status[name] = name + " has been uploaded"
        else:
            status[name] = name + " file already exists"
        if "status" in status:
            status.pop("status")
        return status

    def get_file_names(self, report_obj):
        names_list = []
        file_objs = ReportFile.objects.filter(file_report=report_obj)
        for file_obj in file_objs:
            name = file_obj.file.name
            name = name.split('/')[-1]
            names_list.append(name)
        return names_list


class GetUserReportsAPIView(ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = Report.objects.all()

    def list(self, request, *args, **kwargs):
        user = self.request.user
        report_objs = Report.objects.filter(user=user)
        reports = []
        for report_obj in report_objs:
            serializer = ReportSerializer(report_obj)

            data = serializer.data
            file_objs = ReportFile.objects.filter(file_report=report_obj)
            files = []
            for file_obj in file_objs:
                files.append(file_obj.file.url)
            data['files'] = files
            reports.append(data)
        return Response({"data": reports}, status=HTTP_200_OK)
